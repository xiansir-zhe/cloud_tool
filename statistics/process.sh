#!/bin/bash

# 实例响应处理工具启动脚本

# 默认文件名
INPUT_FILE="responses.txt"
OUTPUT_FILE="results.csv"

# 显示帮助信息
show_help() {
    echo "实例响应处理工具"
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  -i, --input FILE   指定输入文件 (默认: responses.txt)"
    echo "  -o, --output FILE  指定输出文件 (默认: results.csv)"
    echo "  -h, --help         显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0 -i my_responses.txt -o my_results.csv"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--input)
            INPUT_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "错误: 未知参数 $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查输入文件是否存在
if [ ! -f "$INPUT_FILE" ]; then
    echo "错误: 输入文件 '$INPUT_FILE' 不存在"
    exit 1
fi

# 运行Python脚本
echo "正在处理数据..."
python3 process_responses.py "$INPUT_FILE" "$OUTPUT_FILE"

# 显示生成的CSV文件的前几行
if [ -f "$OUTPUT_FILE" ]; then
    echo
    echo "生成的CSV文件前5行内容:"
    head -n 5 "$OUTPUT_FILE"
fi

if [ -f "statistics.csv" ]; then
    echo
    echo "统计信息:"
    cat "statistics.csv"
fi

echo
echo "处理完成!" 