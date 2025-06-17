#!/usr/bin/env python3
"""
DICOM2NII Pro - 批量转换测试脚本

测试转换管理器和批量处理器的功能
"""

import os
import sys
import time
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.conversion_manager import ConversionManager
from src.core.batch_processor import BatchProcessor


def setup_logging():
    """设置日志记录"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('batch_conversion_test.log')
        ]
    )


def test_batch_scan_and_conversion():
    """测试批量扫描和转换功能"""
    logger = logging.getLogger(__name__)
    
    # 测试数据路径
    test_data_path = Path("../dic2nii")
    output_path = Path("test_output")
    
    if not test_data_path.exists():
        logger.error(f"测试数据路径不存在: {test_data_path}")
        return False
    
    # 创建输出目录
    output_path.mkdir(exist_ok=True)
    
    logger.info("🚀 开始批量转换测试")
    
    try:
        # 1. 创建转换管理器
        logger.info("📝 创建转换管理器...")
        conversion_manager = ConversionManager(max_workers=2, auto_start=True)
        
        # 添加进度回调
        def progress_callback(task_id: str, progress: float, message: str):
            logger.info(f"任务 {task_id}: {progress*100:.1f}% - {message}")
        
        def completion_callback(task):
            logger.info(f"✅ 任务 {task.task_id} 完成: {task.output_path}")
        
        def error_callback(task, error):
            logger.error(f"❌ 任务 {task.task_id} 失败: {error}")
        
        conversion_manager.add_progress_callback(progress_callback)
        conversion_manager.add_completion_callback(completion_callback)
        conversion_manager.add_error_callback(error_callback)
        
        # 2. 创建批量处理器
        logger.info("📁 创建批量处理器...")
        batch_processor = BatchProcessor(conversion_manager)
        
        # 3. 扫描测试数据
        logger.info(f"🔍 扫描测试数据目录: {test_data_path}")
        scan_result = batch_processor.scan_directory(
            test_data_path,
            recursive=True,
            modality_filter=['CT']  # 只处理CT数据
        )
        
        # 4. 显示扫描结果
        summary = scan_result.get_summary()
        logger.info(f"📊 扫描结果摘要:")
        logger.info(f"   - 总DICOM文件: {summary['total_dicom_files']}")
        logger.info(f"   - 有效文件: {summary['valid_dicom_files']}")
        logger.info(f"   - 序列数量: {summary['total_series']}")
        logger.info(f"   - 患者数量: {summary['total_patients']}")
        logger.info(f"   - 模态分布: {summary['modality_distribution']}")
        
        if summary['total_series'] == 0:
            logger.warning("未找到有效的DICOM序列")
            return False
        
        # 5. 生成转换任务
        logger.info("⚙️ 生成转换任务...")
        tasks = batch_processor.generate_conversion_tasks(
            scan_result,
            output_path,
            naming_template="{patient_id}/{modality}_{series_name}",
            conversion_params={'remove_private_tags': True}
        )
        
        logger.info(f"生成了 {len(tasks)} 个转换任务")
        
        if not tasks:
            logger.warning("未生成任何转换任务")
            return False
        
        # 显示前几个任务信息
        for i, task in enumerate(tasks[:3]):
            logger.info(f"任务 {i+1}: {task['input_path']} -> {task['output_path']}")
        
        # 6. 提交批量转换任务
        logger.info("🎯 提交批量转换任务...")
        task_ids = batch_processor.submit_batch_conversion(tasks, conversion_manager)
        
        # 7. 监控转换进度
        logger.info("📈 监控转换进度...")
        start_time = time.time()
        
        while True:
            progress_info = batch_processor.get_conversion_progress(task_ids, conversion_manager)
            
            logger.info(
                f"进度: {progress_info['overall_progress']*100:.1f}% "
                f"(完成: {progress_info['completed']}, "
                f"运行: {progress_info['running']}, "
                f"待处理: {progress_info['pending']}, "
                f"失败: {progress_info['failed']})"
            )
            
            # 检查是否全部完成
            if progress_info['completed'] + progress_info['failed'] >= len(task_ids):
                break
            
            # 超时检查
            if time.time() - start_time > 300:  # 5分钟超时
                logger.warning("转换超时")
                break
            
            time.sleep(5)
        
        # 8. 显示最终结果
        final_progress = batch_processor.get_conversion_progress(task_ids, conversion_manager)
        logger.info("🏁 转换完成!")
        logger.info(f"总任务: {final_progress['total_tasks']}")
        logger.info(f"成功: {final_progress['completed']}")
        logger.info(f"失败: {final_progress['failed']}")
        
        # 显示统计信息
        stats = conversion_manager.get_statistics()
        logger.info(f"📈 统计信息:")
        logger.info(f"   - 平均处理时间: {stats.average_time_per_task:.2f}秒")
        logger.info(f"   - 总处理时间: {stats.total_processing_time:.2f}秒")
        
        # 9. 清理
        conversion_manager.stop_workers()
        logger.info("✅ 测试完成")
        
        return final_progress['completed'] > 0
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_conversion():
    """测试简单转换功能"""
    logger = logging.getLogger(__name__)
    
    test_data_path = Path("../dic2nii/1023-0007-Baseline-head-CT")
    output_file = Path("test_output/simple_test.nii.gz")
    
    if not test_data_path.exists():
        logger.error(f"测试数据路径不存在: {test_data_path}")
        return False
    
    logger.info("🔧 测试简单转换功能")
    
    try:
        # 创建转换管理器
        with ConversionManager(max_workers=1) as manager:
            # 添加任务
            task_id = manager.add_task(
                input_path=test_data_path,
                output_path=output_file,
                modality="CT",
                auto_detect=False
            )
            
            logger.info(f"添加任务: {task_id}")
            
            # 等待完成
            success = manager.wait_for_completion(timeout=60)
            
            if success:
                task = manager.get_task_status(task_id)
                if task and task.status == "completed":
                    logger.info(f"✅ 简单转换测试成功: {output_file}")
                    return True
                else:
                    logger.error(f"❌ 任务失败: {task.error_message if task else 'Unknown'}")
            else:
                logger.error("❌ 转换超时")
        
        return False
        
    except Exception as e:
        logger.error(f"简单转换测试失败: {e}")
        return False


def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🎬 开始DICOM2NII Pro批量转换测试")
    
    # 运行测试
    tests = [
        ("简单转换测试", test_simple_conversion),
        ("批量扫描转换测试", test_batch_scan_and_conversion)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"开始测试: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            if test_func():
                logger.info(f"✅ {test_name} 通过")
                passed += 1
            else:
                logger.error(f"❌ {test_name} 失败")
        except Exception as e:
            logger.error(f"❌ {test_name} 异常: {e}")
    
    # 输出测试结果
    logger.info(f"\n{'='*50}")
    logger.info(f"测试结果: {passed}/{total} 通过")
    logger.info(f"{'='*50}")
    
    if passed == total:
        logger.info("🎉 所有测试通过!")
        return 0
    else:
        logger.error("💥 部分测试失败!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 