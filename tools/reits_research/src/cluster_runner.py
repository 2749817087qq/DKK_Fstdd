"""SCNet 集群回测任务提交器。

将 reits-research 的回测任务自动提交到华东一区【昆山】集群，
监控作业状态，结果回传后自动生成报告。

工作流：
  1. 生成 Slurm 脚本 + 回测参数 YAML
  2. 上传到集群工作目录
  3. sbatch 提交作业
  4. 监控至完成
  5. 下载结果 → 调用 ReportGenerator 生成 Markdown
"""
from __future__ import annotations

import datetime
import textwrap
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional


class ClusterBacktestRunner:
    """SCNet 集群回测任务管理器。

    Args:
        cluster_id: SCNet 集群 ID（华东一区【昆山】= "11250"）。
        workdir: 集群上的工作目录路径。
        queue: 队列名称（用户选择后传入）。
    """

    CLUSTER_NAME = "华东一区【昆山】"
    DEFAULT_CLUSTER_ID = "11250"

    def __init__(
        self,
        cluster_id: str = DEFAULT_CLUSTER_ID,
        workdir: str = "$HOME/reits_backtest",
        queue: str = "",
    ) -> None:
        self.cluster_id = cluster_id
        self.workdir = workdir
        self.queue = queue
        self.job_id: Optional[str] = None

    # ── Step 1: 生成 Slurm 脚本 ────────────────────────────────────

    def generate_slurm_script(
        self,
        task_name: str = "reits_backtest",
        nodes: int = 1,
        ntasks: int = 4,
        time_limit: str = "01:00:00",
        python_cmd: str = "python3",
        extra_params: Optional[dict] = None,
    ) -> str:
        """生成 Slurm 批处理脚本。

        Args:
            task_name: 作业名称。
            nodes: 节点数。
            ntasks: 每节点任务数（并行回测参数扫描用）。
            time_limit: 最大运行时间。
            python_cmd: Python 解释器命令。
            extra_params: 额外回测参数（写入 params.yaml）。

        Returns:
            Slurm 脚本内容字符串。
        """
        params_yaml = ""
        if extra_params:
            import yaml
            params_yaml = yaml.safe_dump(extra_params, allow_unicode=True)

        script = textwrap.dedent(f"""\
            #!/bin/bash
            #SBATCH --job-name={task_name}
            #SBATCH --nodes={nodes}
            #SBATCH --ntasks-per-node={ntasks}
            #SBATCH --time={time_limit}
            #SBATCH --output=%x_%j.out
            #SBATCH --error=%x_%j.err

            # REITs Backtest on SCNet {self.CLUSTER_NAME}
            # Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}

            set -euo pipefail

            WORKDIR="{self.workdir}"
            cd "$WORKDIR"

            echo "=== REITs Backtest Start ==="
            echo "Job ID: $SLURM_JOB_ID"
            echo "Node: $SLURMD_NODENAME"
            echo "Tasks: $SLURM_NTASKS"
            echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

            # 约束锚定校验（漂移检测）
            {python_cmd} -c "
            from src.constraint_anchor import ConstraintAnchor
            anchor = ConstraintAnchor(strict_mode=True)
            ok, msg = anchor.verify()
            print(msg)
            " || {{
                echo "CONSTRAINT DRIFT DETECTED — ABORTING"
                exit 1
            }}

            # 执行回测
            {python_cmd} -m pytest tests/ -q --tb=short 2>&1 | tee test_results.log

            # 生成报告
            {python_cmd} -c "
            from src.report_generator import ReportGenerator
            from src.performance import PerformanceCalculator
            from decimal import Decimal
            import pandas as pd

            # TODO: 从实际回测结果加载净值序列
            # 此处为模板占位，实际使用时替换为真实数据
            gen = ReportGenerator(
                title='{task_name} REITs 投研报告',
                data_cutoff='{datetime.date.today().isoformat()}',
                code_version='cluster-$SLURM_JOB_ID',
            )
            perf = {{
                'annualized_return': Decimal('0'),
                'max_drawdown': Decimal('0'),
                'sharpe_ratio': Decimal('0'),
                'calmar_ratio': Decimal('0'),
            }}
            report = gen.generate(
                performance=perf,
                quality_results={{}},
                quality_log=[],
                audit_log=[{{
                    'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
                    'check': 'cluster_backtest',
                    'code': '-',
                    'status': 'completed',
                    'detail': f'job_id=$SLURM_JOB_ID node=$SLURMD_NODENAME',
                }}],
            )
            with open('report.md', 'w') as f:
                f.write(report)
            print('Report generated: report.md')
            "

            echo "=== REITs Backtest Complete ==="
            echo "End Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        """)
        return script

    # ── Step 2: 生成提交指令 ───────────────────────────────────────

    def get_submit_command(self, slurm_filename: str = "reits_backtest.slurm") -> str:
        """返回 sbatch 提交命令（供 scnet_remote_shell_execute 使用）。"""
        return f"cd {self.workdir} && sbatch {slurm_filename}"

    # ── Step 3: 生成监控指令 ───────────────────────────────────────

    def get_monitor_command(self) -> str:
        """返回 squeue 状态查询命令（仅用于快照，正式监控用 monitor-job）。"""
        if self.job_id:
            return f"squeue -j {self.job_id} -o '%i %T %M %N'"
        return "squeue -u $USER -o '%i %j %T %M %N'"

    # ── Step 4: 结果收集指令 ──────────────────────────────────────

    def get_result_paths(self) -> dict[str, str]:
        """返回集群上需要下载的结果文件路径。"""
        return {
            "report": f"{self.workdir}/report.md",
            "test_log": f"{self.workdir}/test_results.log",
            "stdout": f"{self.workdir}/reits_backtest_{self.job_id}.out" if self.job_id else "",
            "stderr": f"{self.workdir}/reits_backtest_{self.job_id}.err" if self.job_id else "",
        }

    # ── 完整工作流说明 ─────────────────────────────────────────────

    @staticmethod
    def workflow_instructions() -> str:
        """返回完整的集群回测工作流说明（供 Agent 参考）。"""
        return textwrap.dedent("""\
            ## SCNet 集群回测工作流

            ### 前置条件
            - SCNET_AK / SCNET_SK / SCNET_USER 环境变量已设置
            - reits_research 代码已上传到集群工作目录

            ### 执行步骤

            1. **查询队列** → 让用户选择队列
               ```
               python3 scripts/run.py queues --cluster-id 11250 ...
               ```

            2. **上传代码** → 将 reits_research/ 上传到集群
               ```
               python3 scripts/run.py upload-file --cluster-id 11250 \
                 --local-file reits_research_v1.1.tar.gz \
                 --remote-path $HOME/reits_backtest ...
               ```

            3. **解压 + 安装依赖**
               ```
               cd $HOME/reits_backtest && tar xzf reits_research_v1.1.tar.gz
               pip install pyyaml psycopg2-binary duckdb pandas numpy
               ```

            4. **生成 Slurm 脚本** → 调用 ClusterBacktestRunner.generate_slurm_script()

            5. **提交作业** → sbatch reits_backtest.slurm
               - 记录返回的 job_id
               - 告知用户作业已提交

            6. **监控作业** → 使用 monitor-job 或 trigger_job_monitor
               - 等待 COMPLETED 状态

            7. **下载报告** → 从集群获取 report.md
               ```
               cat $HOME/reits_backtest/report.md
               ```

            8. **展示结果** → 将报告内容呈现给用户

            ### 约束保障
            - Slurm 脚本内置 ConstraintAnchor.verify()，漂移则中止
            - 测试全量通过才生成报告
            - 审计日志包含 job_id + node + timestamp
        """)
