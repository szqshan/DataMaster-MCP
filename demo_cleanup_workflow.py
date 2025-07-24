#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库清理功能演示脚本
展示完整的AI主动数据库管理工作流程
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import get_data_info, execute_database_cleanup
import json

def demo_ai_database_management():
    """演示AI主动数据库管理功能"""
    print("🤖 AI数据库管理助手启动")
    print("=" * 50)
    
    # 步骤1: 分析数据库，检测过时数据
    print("\n📊 步骤1: 分析数据库，检测过时数据...")
    try:
        cleanup_analysis = get_data_info(info_type="cleanup")
        print("✅ 数据库分析完成")
        
        # 解析分析结果
        import json
        analysis_data = json.loads(cleanup_analysis.split('\n\n')[1])
        
        stats = analysis_data['data']['cleanup_stats']
        cleanup_suggestions = analysis_data['data']['cleanup_suggestions']
        
        print(f"\n📈 数据库统计:")
        print(f"  • 总表数: {stats['total_tables']}")
        print(f"  • 测试表: {stats['test_tables_count']}")
        print(f"  • 空表: {stats['empty_tables_count']}")
        print(f"  • 重复表: {stats['duplicate_tables_count']}")
        print(f"  • 历史表: {stats['old_tables_count']}")
        print(f"  • 总问题数: {stats['total_issues']}")
        print(f"  • 高优先级: {stats['high_priority_issues']}")
        print(f"  • 中优先级: {stats['medium_priority_issues']}")
        print(f"  • 低优先级: {stats['low_priority_issues']}")
        
        # 获取建议删除的表
        high_priority_tables = []
        medium_priority_tables = []
        
        for suggestion in cleanup_suggestions:
            category_name = suggestion['category']
            priority = suggestion['priority']
            tables = suggestion['tables']
            
            if priority == 'HIGH':
                high_priority_tables.extend([t['table_name'] for t in tables])
            elif priority == 'MEDIUM':
                medium_priority_tables.extend([t['table_name'] for t in tables])
        
        print(f"\n🎯 清理建议:")
        print(f"  • 高优先级清理: {len(high_priority_tables)} 个表")
        print(f"  • 中优先级清理: {len(medium_priority_tables)} 个表")
        
        # 步骤2: AI询问用户是否清理
        if high_priority_tables or medium_priority_tables:
            print("\n🤔 AI建议: 检测到可以清理的过时数据")
            
            if high_priority_tables:
                print(f"\n⚠️ 建议立即清理以下 {len(high_priority_tables)} 个表（测试表/空表）:")
                for i, table in enumerate(high_priority_tables[:5], 1):  # 只显示前5个
                    print(f"  {i}. {table}")
                if len(high_priority_tables) > 5:
                    print(f"  ... 还有 {len(high_priority_tables) - 5} 个表")
                
                # 模拟用户确认
                print("\n❓ 是否清理这些高优先级表？ (在实际使用中，AI会询问用户)")
                user_confirm_high = "y"  # 模拟用户确认
                print(f"👤 用户回复: {user_confirm_high}")
                
                if user_confirm_high.lower() == 'y':
                    # 步骤3: 预览删除操作
                    print("\n🔍 步骤3: 预览删除操作...")
                    preview_result = execute_database_cleanup(
                        action="preview_deletion",
                        tables_to_clean=high_priority_tables[:3]  # 只预览前3个
                    )
                    print("✅ 删除预览完成")
                    
                    # 解析预览结果
                    preview_data = json.loads(preview_result.split('\n\n')[1])
                    total_rows = preview_data['data']['total_rows_affected']
                    tables_count = preview_data['data']['tables_to_delete']
                    
                    print(f"\n📋 预览结果:")
                    print(f"  • 将删除 {tables_count} 个表")
                    print(f"  • 影响 {total_rows} 行数据")
                    
                    # 步骤4: 执行清理（演示模式，不实际删除）
                    print("\n🧹 步骤4: 执行清理操作...")
                    print("⚠️ 演示模式：不会实际删除数据")
                    print("💡 实际使用时的命令:")
                    print(f"   execute_database_cleanup(")
                    print(f"       action='delete_tables',")
                    print(f"       tables_to_clean={high_priority_tables[:3]},")
                    print(f"       confirm_deletion=True")
                    print(f"   )")
                    
                    print("\n✅ 清理操作完成（演示）")
                else:
                    print("\n⏭️ 用户选择跳过高优先级清理")
            
            if medium_priority_tables:
                print(f"\n💡 还有 {len(medium_priority_tables)} 个中优先级表可以考虑清理")
                print("   （重复表和历史表，建议人工审查后决定）")
        else:
            print("\n✨ 数据库很整洁，暂无需要清理的数据")
            
    except Exception as e:
        print(f"❌ 数据库管理失败: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 AI数据库管理演示完成！")
    print("\n📚 功能特点:")
    print("  ✅ 智能检测过时数据（测试表、空表、重复表、历史表）")
    print("  ✅ 分优先级提供清理建议")
    print("  ✅ 安全预览删除操作")
    print("  ✅ 用户确认机制")
    print("  ✅ 详细的操作日志")
    print("\n🔧 集成到MCP工具中，AI可以主动管理数据库整洁度！")
    
    return True

if __name__ == "__main__":
    demo_ai_database_management()