import re
import json
import csv
import sys
import ast
from collections import Counter

def extract_instance_info(response_str):
    # 提取实例ID
    instance_id_match = re.search(r'Instance (ins-[a-zA-Z0-9]+)', response_str)
    instance_id = instance_id_match.group(1) if instance_id_match else "未知"
    
    # 尝试解析JSON部分
    try:
        # 找到JSON部分
        json_part_match = re.search(r'response: (.*$)', response_str.strip())
        if not json_part_match:
            raise Exception("无法识别响应格式")
            
        json_str = json_part_match.group(1).strip()
        # 使用ast.literal_eval更安全地解析Python字典字符串
        response_data = ast.literal_eval(json_str)
        
        # 确定状态信息
        status = "成功"
        status_message = "操作成功完成"
        
        # 检查是否有错误信息
        if 'code' in response_data and response_data['code'] != 0:
            status = "失败"
            if 'message' in response_data:
                status_message = response_data['message']
            elif 'data' in response_data and 'Response' in response_data['data'] and 'Error' in response_data['data']['Response']:
                status_message = response_data['data']['Response']['Error']['Message']
        
        # 如果有TaskId，记录下来
        task_id = "无"
        if 'data' in response_data and 'Response' in response_data['data'] and 'TaskId' in response_data['data']['Response']:
            task_id = response_data['data']['Response']['TaskId']
            
        return {
            "instance_id": instance_id,
            "status": status,
            "message": status_message,
            "task_id": task_id
        }
    except Exception as e:
        return {
            "instance_id": instance_id,
            "status": "解析错误",
            "message": f"无法解析响应: {str(e)}",
            "task_id": "无"
        }

def generate_statistics(results):
    """生成统计信息"""
    total = len(results)
    status_count = Counter([r["status"] for r in results])
    
    print("\n===== 统计信息 =====")
    print(f"总实例数: {total}")
    print(f"成功: {status_count.get('成功', 0)} ({status_count.get('成功', 0)/total*100:.1f}%)")
    print(f"失败: {status_count.get('失败', 0)} ({status_count.get('失败', 0)/total*100:.1f}%)")
    print(f"解析错误: {status_count.get('解析错误', 0)} ({status_count.get('解析错误', 0)/total*100:.1f}%)")
    
    # 错误信息统计
    if status_count.get('失败', 0) > 0:
        error_messages = [r["message"] for r in results if r["status"] == "失败"]
        error_count = Counter(error_messages)
        
        print("\n错误信息统计:")
        for error, count in error_count.most_common():
            print(f"- {error}: {count}次 ({count/status_count.get('失败', 0)*100:.1f}%)")
    
    # 写入统计信息到CSV
    stats_file = "statistics.csv"
    with open(stats_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["指标", "数值", "百分比"])
        writer.writerow(["总实例数", total, "100%"])
        writer.writerow(["成功", status_count.get('成功', 0), f"{status_count.get('成功', 0)/total*100:.1f}%"])
        writer.writerow(["失败", status_count.get('失败', 0), f"{status_count.get('失败', 0)/total*100:.1f}%"])
        writer.writerow(["解析错误", status_count.get('解析错误', 0), f"{status_count.get('解析错误', 0)/total*100:.1f}%"])
        
        if status_count.get('失败', 0) > 0:
            writer.writerow([])
            writer.writerow(["错误信息", "次数", "占失败比例"])
            for error, count in error_count.most_common():
                writer.writerow([error, count, f"{count/status_count.get('失败', 0)*100:.1f}%"])
    
    print(f"\n统计信息已保存到 {stats_file}")

def process_responses(input_file, output_file):
    # 读取输入文件
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 分割多个响应 - 使用空行分割
    responses = content.split("\n\n")
    responses = [r.strip() for r in responses if r.strip()]  # 移除空字符串
    
    # 处理每个响应
    results = []
    for response in responses:
        if not response.startswith("Instance"):
            continue
        result = extract_instance_info(response)
        results.append(result)
    
    # 写入CSV文件
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["instance_id", "status", "message", "task_id"])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"处理完成！共处理了 {len(results)} 个实例响应，结果已保存到 {output_file}")
    
    # 生成统计信息
    generate_statistics(results)
    
    return results

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用方式：python process_responses.py 输入文件路径 输出文件路径")
        print("例如：python process_responses.py responses.txt results.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    process_responses(input_file, output_file) 