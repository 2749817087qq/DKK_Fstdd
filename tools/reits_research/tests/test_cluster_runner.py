"""集群回测提交器测试。"""
from __future__ import annotations

import pytest


class TestSlurmGeneration:
    """Slurm 脚本生成验证。"""

    def test_slurm_script_contains_directives(self):
        """GIVEN 有效参数 WHEN 生成脚本 THEN 包含 SBATCH 指令。"""
        from src.cluster_runner import ClusterBacktestRunner

        runner = ClusterBacktestRunner(queue="compute")
        script = runner.generate_slurm_script(task_name="test_bt", ntasks=8)

        assert "#SBATCH --job-name=test_bt" in script
        assert "#SBATCH --ntasks-per-node=8" in script
        assert "ConstraintAnchor" in script  # 约束校验嵌入

    def test_slurm_script_contains_constraint_check(self):
        """GIVEN 生成脚本 WHEN 检查 THEN 包含漂移检测代码。"""
        from src.cluster_runner import ClusterBacktestRunner

        runner = ClusterBacktestRunner()
        script = runner.generate_slurm_script()

        assert "CONSTRAINT DRIFT DETECTED" in script
        assert "strict_mode=True" in script

    def test_submit_command_format(self):
        """GIVEN runner WHEN 获取提交命令 THEN 格式正确。"""
        from src.cluster_runner import ClusterBacktestRunner

        runner = ClusterBacktestRunner(workdir="$HOME/my_bt")
        cmd = runner.get_submit_command("run.slurm")

        assert "sbatch run.slurm" in cmd
        assert "$HOME/my_bt" in cmd


class TestWorkflowInstructions:
    """工作流说明完整性。"""

    def test_instructions_contain_all_steps(self):
        """GIVEN 工作流说明 WHEN 检查 THEN 包含全部8个步骤。"""
        from src.cluster_runner import ClusterBacktestRunner

        instructions = ClusterBacktestRunner.workflow_instructions()

        assert "查询队列" in instructions
        assert "上传代码" in instructions
        assert "提交作业" in instructions
        assert "监控作业" in instructions
        assert "下载报告" in instructions
        assert "ConstraintAnchor" in instructions
