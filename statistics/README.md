# 实例响应处理工具

这个工具用于批量处理腾讯云实例操作的响应信息，并将结果导出为CSV文件。

## 功能

- 解析腾讯云实例的操作响应
- 提取实例ID、操作状态、错误信息等
- 生成CSV文件用于统计分析
- 自动生成统计信息报表

## 使用方法

1. 准备一个包含实例响应信息的文本文件，例如 `responses.txt`
2. 运行以下命令：

```
python3 process_responses.py responses.txt results.csv
```

3. 查看生成的CSV文件 `results.csv` 和统计信息 `statistics.csv`

## 输出文件

### results.csv 字段说明

- `instance_id`: 实例ID，例如 ins-mulr52gb
- `status`: 操作状态，成功/失败
- `message`: 状态信息或错误信息
- `task_id`: 任务ID（如果有）

### statistics.csv 字段说明

- 基本统计信息：总实例数、成功数、失败数及其百分比
- 错误信息统计：各类错误信息出现的次数及占失败总数的百分比

## 示例

输入 `responses.txt`：
```
Instance ins-mulr52gb stop response: {'data': {'Response': {'Error': {'Code': 'UnsupportedOperation.InstanceStateStopped', 'Message': '不支持状态为已关机的实例ins-mulr52gb (0ab53883)'}, 'RequestId': '0ab53883-b3cc-4c6e-a404-1c30b9993dd1'}}, 'message': '不支持状态为已关机的实例ins-mulr52gb (0ab53883)', 'code': 'UnsupportedOperation.InstanceStateStopped'}

Instance ins-bbijxjyd stop response: {'data': {'Response': {'TaskId': '2079158371', 'flowId': 2079158371, 'RequestId': 'a7db861f-c369-4c41-8634-90d56a8800c2'}}, 'code': 0}
```

输出 `results.csv`：
```
instance_id,status,message,task_id
ins-mulr52gb,失败,不支持状态为已关机的实例ins-mulr52gb (0ab53883),无
ins-bbijxjyd,成功,操作成功完成,2079158371
```

输出 `statistics.csv`：
```
指标,数值,百分比
总实例数,2,100%
成功,1,50.0%
失败,1,50.0%
解析错误,0,0.0%

错误信息,次数,占失败比例
不支持状态为已关机的实例ins-mulr52gb (0ab53883),1,100.0%
```

## 注意事项

- 输入文件中的每个实例响应必须以"Instance"开头，并以空行分隔
- 响应格式必须符合示例中的格式，即包含实例ID和JSON格式的响应内容 