"""
数据校验模块
对清洗后的数据进行校验，生成错误和警告报告
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class ValidationIssue:
    """校验问题记录"""
    row_number: int
    severity: str  # 'error' 或 'warning'
    field: str
    message: str
    value: Optional[str] = None


@dataclass
class ValidationReport:
    """校验报告"""
    total_rows: int = 0
    success_rows: int = 0
    warning_rows: int = 0
    error_rows: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    
    def add_issue(
        self, 
        row_number: int, 
        severity: str, 
        field: str, 
        message: str,
        value: Optional[str] = None
    ) -> None:
        """添加校验问题"""
        self.issues.append(
            ValidationIssue(
                row_number=row_number,
                severity=severity,
                field=field,
                message=message,
                value=value
            )
        )
        
        if severity == 'error':
            self.error_rows += 1
        elif severity == 'warning':
            self.warning_rows += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """获取摘要统计"""
        return {
            'total_rows': self.total_rows,
            'success_rows': self.success_rows,
            'warning_rows': self.warning_rows,
            'error_rows': self.error_rows,
            'total_issues': len(self.issues)
        }
    
    def get_issues_by_severity(self, severity: str) -> List[ValidationIssue]:
        """获取指定严重程度的问题"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def format_report(self, max_issues: int = 10) -> str:
        """格式化报告为人类可读的字符串"""
        lines = []
        lines.append("=" * 60)
        lines.append("数据校验报告")
        lines.append("=" * 60)
        
        summary = self.get_summary()
        lines.append(f"总行数: {summary['total_rows']}")
        lines.append(f"成功行数: {summary['success_rows']}")
        lines.append(f"警告行数: {summary['warning_rows']}")
        lines.append(f"错误行数: {summary['error_rows']}")
        lines.append(f"总问题数: {summary['total_issues']}")
        lines.append("")
        
        # 显示错误
        errors = self.get_issues_by_severity('error')
        if errors:
            lines.append(f"错误 ({len(errors)} 条):")
            for issue in errors[:max_issues]:
                lines.append(
                    f"  行 {issue.row_number} | {issue.field}: {issue.message}"
                )
                if issue.value:
                    lines.append(f"    值: {issue.value}")
            if len(errors) > max_issues:
                lines.append(f"  ... 还有 {len(errors) - max_issues} 条错误未显示")
            lines.append("")
        
        # 显示警告
        warnings = self.get_issues_by_severity('warning')
        if warnings:
            lines.append(f"警告 ({len(warnings)} 条):")
            for issue in warnings[:max_issues]:
                lines.append(
                    f"  行 {issue.row_number} | {issue.field}: {issue.message}"
                )
                if issue.value:
                    lines.append(f"    值: {issue.value}")
            if len(warnings) > max_issues:
                lines.append(f"  ... 还有 {len(warnings) - max_issues} 条警告未显示")
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


class DataValidator:
    """数据校验器"""
    
    def __init__(self, config: dict):
        """
        初始化校验器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.role_whitelist = config.get('cleaning_rules', {}).get('role_whitelist', [])
    
    def validate_dataframe(self, df: pd.DataFrame) -> ValidationReport:
        """
        校验整个 DataFrame
        
        Args:
            df: 要校验的 DataFrame
            
        Returns:
            ValidationReport 对象
        """
        report = ValidationReport()
        report.total_rows = len(df)
        
        # 记录每行是否有错误
        row_has_error = [False] * len(df)
        row_has_warning = [False] * len(df)
        
        for idx, row in df.iterrows():
            row_num = idx + 2  # +2 因为：索引从0开始，且有表头行
            
            # 校验必填字段
            self._validate_required_fields(row, row_num, report)
            
            # 校验日期格式
            self._validate_date(row, row_num, report)
            
            # 校验重复记录（在后续步骤中处理）
            
            # 检查是否有错误或警告
            for issue in report.issues:
                if issue.row_number == row_num:
                    if issue.severity == 'error':
                        row_has_error[idx] = True
                    elif issue.severity == 'warning':
                        row_has_warning[idx] = True
        
        # 校验重复的 service_date + service_slot
        self._validate_duplicates(df, report)
        
        # 更新重复警告的行标记
        for issue in report.issues:
            if issue.message.startswith('重复的服务记录'):
                idx = issue.row_number - 2
                if 0 <= idx < len(row_has_warning):
                    row_has_warning[idx] = True
        
        # 计算成功行数
        for idx in range(len(df)):
            if not row_has_error[idx]:
                report.success_rows += 1
        
        return report
    
    def _validate_required_fields(
        self, 
        row: pd.Series, 
        row_num: int, 
        report: ValidationReport
    ) -> None:
        """校验必填字段"""
        required_fields = ['service_date']
        
        for field in required_fields:
            if field not in row:
                continue
            
            value = row[field]
            if pd.isna(value) or not str(value).strip():
                report.add_issue(
                    row_num,
                    'error',
                    field,
                    f"必填字段 '{field}' 不能为空",
                    str(value)
                )
    
    def _validate_date(
        self, 
        row: pd.Series, 
        row_num: int, 
        report: ValidationReport
    ) -> None:
        """校验日期格式"""
        if 'service_date' not in row:
            return
        
        date_val = row['service_date']
        if pd.isna(date_val) or not str(date_val).strip():
            return  # 空值已在必填字段校验中处理
        
        date_str = str(date_val).strip()
        
        # 检查是否符合 YYYY-MM-DD 格式
        import re
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            report.add_issue(
                row_num,
                'error',
                'service_date',
                f"日期格式不正确，应为 YYYY-MM-DD",
                date_str
            )
            return
        
        # 验证日期有效性
        from datetime import datetime
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            report.add_issue(
                row_num,
                'error',
                'service_date',
                f"无效的日期",
                date_str
            )
    
    def _validate_duplicates(
        self, 
        df: pd.DataFrame, 
        report: ValidationReport
    ) -> None:
        """检查重复的服务记录（同一日期和时段）"""
        if 'service_date' not in df.columns:
            return
        
        # 确定要检查的列
        group_cols = ['service_date']
        if 'service_slot' in df.columns:
            group_cols.append('service_slot')
        
        # 查找重复
        duplicates = df[df.duplicated(subset=group_cols, keep=False)]
        
        if not duplicates.empty:
            for idx in duplicates.index:
                row_num = idx + 2
                date_val = df.loc[idx, 'service_date']
                slot_val = df.loc[idx, 'service_slot'] if 'service_slot' in df.columns else 'N/A'
                
                report.add_issue(
                    row_num,
                    'warning',
                    'service_date',
                    f"重复的服务记录（日期: {date_val}, 时段: {slot_val}）",
                    f"{date_val}_{slot_val}"
                )
    
    def validate_role(self, role: str) -> bool:
        """
        校验角色是否在白名单中
        
        Args:
            role: 角色名称
            
        Returns:
            是否有效
        """
        if not self.role_whitelist:
            return True
        
        return role in self.role_whitelist

