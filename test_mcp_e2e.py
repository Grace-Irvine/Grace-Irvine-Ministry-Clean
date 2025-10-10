#!/usr/bin/env python3
"""
MCP End-to-End 测试脚本
测试所有MCP工具功能，验证返回预期内容
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
import traceback

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 从重命名后的mcp_local目录导入
from mcp_local.mcp_server import server, handle_call_tool

class MCPE2ETester:
    def __init__(self):
        self.test_results = []
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_test(self, test_name: str, success: bool, result: Any = None, error: str = None):
        """记录测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        
        if error:
            print(f"   错误: {error}")
        
        if result and success:
            # 处理MCP返回的TextContent对象
            if hasattr(result, 'content'):
                result_str = str(result.content)[:100]
            else:
                result_str = str(result)[:100]
            print(f"   结果: {result_str}{'...' if len(str(result)) > 100 else ''}")
        
        # 安全地序列化结果
        serializable_result = None
        if result:
            if hasattr(result, 'content'):
                serializable_result = str(result.content)
            elif hasattr(result, '__dict__'):
                serializable_result = str(result)
            else:
                serializable_result = str(result)
        
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "result": serializable_result,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        
        if success:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
    
    async def test_query_volunteers_by_date(self):
        """测试查询指定日期的同工服侍安排"""
        test_name = "query_volunteers_by_date"
        try:
            # 测试下个主日
            next_sunday = (datetime.now() + timedelta(days=(6 - datetime.now().weekday()) % 7 + 7)).strftime("%Y-%m-%d")
            
            result = await handle_call_tool("query_volunteers_by_date", {
                "date": next_sunday,
                "year": "2025"
            })
            
            # 验证返回结果 - MCP返回的是TextContent对象
            if result:
                self.log_test(test_name, True, result)
            else:
                self.log_test(test_name, False, result, "返回结果为空")
                
        except Exception as e:
            self.log_test(test_name, False, None, str(e))
    
    async def test_query_sermon_by_date(self):
        """测试查询指定日期的证道信息"""
        test_name = "query_sermon_by_date"
        try:
            # 测试下个主日
            next_sunday = (datetime.now() + timedelta(days=(6 - datetime.now().weekday()) % 7 + 7)).strftime("%Y-%m-%d")
            
            result = await handle_call_tool("query_sermon_by_date", {
                "date": next_sunday,
                "year": "2025"
            })
            
            # 验证返回结果 - MCP返回的是TextContent对象
            if result:
                self.log_test(test_name, True, result)
            else:
                self.log_test(test_name, False, result, "返回结果为空")
                
        except Exception as e:
            self.log_test(test_name, False, None, str(e))
    
    async def test_query_date_range(self):
        """测试查询一段时间范围内的所有服侍安排"""
        test_name = "query_date_range"
        try:
            # 测试未来两周
            start_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
            
            result = await handle_call_tool("query_date_range", {
                "start_date": start_date,
                "end_date": end_date,
                "year": "2025"
            })
            
            # 验证返回结果 - MCP返回的是TextContent对象
            if result:
                self.log_test(test_name, True, result)
            else:
                self.log_test(test_name, False, result, "返回结果为空")
                
        except Exception as e:
            self.log_test(test_name, False, None, str(e))
    
    async def test_check_upcoming_completeness(self):
        """测试检查未来排班完整性"""
        test_name = "check_upcoming_completeness"
        try:
            result = await handle_call_tool("check_upcoming_completeness", {
                "weeks_ahead": 4,
                "year": "2025"
            })
            
            # 验证返回结果 - MCP返回的是TextContent对象
            if result:
                self.log_test(test_name, True, result)
            else:
                self.log_test(test_name, False, result, "返回结果为空")
                
        except Exception as e:
            self.log_test(test_name, False, None, str(e))
    
    async def test_generate_weekly_preview(self):
        """测试生成指定日期的主日预览报告"""
        test_name = "generate_weekly_preview"
        try:
            # 测试下个主日
            next_sunday = (datetime.now() + timedelta(days=(6 - datetime.now().weekday()) % 7 + 7)).strftime("%Y-%m-%d")
            
            result = await handle_call_tool("generate_weekly_preview", {
                "date": next_sunday,
                "year": "2025"
            })
            
            # 验证返回结果 - MCP返回的是TextContent对象
            if result:
                self.log_test(test_name, True, result)
            else:
                self.log_test(test_name, False, result, "返回结果为空")
                
        except Exception as e:
            self.log_test(test_name, False, None, str(e))
    
    async def test_analyze_role_coverage(self):
        """测试分析岗位覆盖率"""
        test_name = "analyze_role_coverage"
        try:
            result = await handle_call_tool("analyze_role_coverage", {
                "weeks_back": 8,
                "year": "2025"
            })
            
            # 验证返回结果 - MCP返回的是TextContent对象
            if result:
                self.log_test(test_name, True, result)
            else:
                self.log_test(test_name, False, result, "返回结果为空")
                
        except Exception as e:
            self.log_test(test_name, False, None, str(e))
    
    async def test_analyze_preacher_rotation(self):
        """测试分析讲员轮换模式"""
        test_name = "analyze_preacher_rotation"
        try:
            result = await handle_call_tool("analyze_preacher_rotation", {
                "weeks_back": 12,
                "year": "2025"
            })
            
            # 验证返回结果 - MCP返回的是TextContent对象
            if result:
                self.log_test(test_name, True, result)
            else:
                self.log_test(test_name, False, result, "返回结果为空")
                
        except Exception as e:
            self.log_test(test_name, False, None, str(e))
    
    async def test_analyze_sermon_series_progress(self):
        """测试追踪证道系列进度"""
        test_name = "analyze_sermon_series_progress"
        try:
            result = await handle_call_tool("analyze_sermon_series_progress", {
                "year": "2025"
            })
            
            # 验证返回结果 - MCP返回的是TextContent对象
            if result:
                self.log_test(test_name, True, result)
            else:
                self.log_test(test_name, False, result, "返回结果为空")
                
        except Exception as e:
            self.log_test(test_name, False, None, str(e))
    
    async def test_analyze_volunteer_trends(self):
        """测试分析同工趋势"""
        test_name = "analyze_volunteer_trends"
        try:
            result = await handle_call_tool("analyze_volunteer_trends", {
                "weeks_back": 12,
                "year": "2025"
            })
            
            # 验证返回结果 - MCP返回的是TextContent对象
            if result:
                self.log_test(test_name, True, result)
            else:
                self.log_test(test_name, False, result, "返回结果为空")
                
        except Exception as e:
            self.log_test(test_name, False, None, str(e))
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("MCP End-to-End 测试开始")
        print("=" * 60)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 运行所有测试
        test_methods = [
            self.test_query_volunteers_by_date,
            self.test_query_sermon_by_date,
            self.test_query_date_range,
            self.test_check_upcoming_completeness,
            self.test_generate_weekly_preview,
            self.test_analyze_role_coverage,
            self.test_analyze_preacher_rotation,
            self.test_analyze_sermon_series_progress,
            self.test_analyze_volunteer_trends
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                print(f"❌ 测试执行异常: {test_method.__name__}")
                print(f"   错误: {str(e)}")
                print(f"   堆栈: {traceback.format_exc()}")
                self.failed_tests += 1
        
        # 生成测试报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        print()
        print("=" * 60)
        print("测试报告")
        print("=" * 60)
        print(f"总测试数: {self.passed_tests + self.failed_tests}")
        print(f"通过: {self.passed_tests}")
        print(f"失败: {self.failed_tests}")
        print(f"成功率: {(self.passed_tests / (self.passed_tests + self.failed_tests) * 100):.1f}%")
        print()
        
        # 保存详细报告
        report_file = f"mcp_e2e_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total_tests": self.passed_tests + self.failed_tests,
                    "passed": self.passed_tests,
                    "failed": self.failed_tests,
                    "success_rate": self.passed_tests / (self.passed_tests + self.failed_tests) * 100
                },
                "test_results": self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"详细报告已保存到: {report_file}")
        
        if self.failed_tests > 0:
            print("\n失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test_name']}: {result['error']}")
        
        return self.failed_tests == 0

async def main():
    """主函数"""
    tester = MCPE2ETester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 所有测试通过！MCP工具运行正常。")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败，请检查配置和日志。")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
