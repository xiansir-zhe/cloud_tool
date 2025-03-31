import csv
import json

csv_file_path = 'cvm_resource.csv'
json_file_path = 'instances.json'

with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    instances = []
    for row in csv_reader:
        instance = {
            "name": row["实例名"],
            "image_id": row["镜像Id"],
            "subnet_id": row["子网Id"],
            "instance_type": row["实例规格"],
            "availability_zone": row["可用区"],
            "vpc_id": row["VpcId"],
            "private_ip": row["主IPv4内网IP"],
            "system_disk": {
                "type": row["系统盘类型"],
                "size": int(row["系统盘大小(GiB)"])
            },
            "data_disks": []
        }

        # Add data disks if they have valid types and sizes
        for i in range(4):
            disk_type_key = f"数据盘_{i}_类型"
            disk_size_key = f"数据盘_{i}_大小（GiB）"
            if row[disk_type_key] and row[disk_size_key]:
                instance["data_disks"].append({
                    "type": row[disk_type_key],
                    "size": int(row[disk_size_key])
                })

        instances.append(instance)

with open(json_file_path, mode='w', encoding='utf-8') as json_file:
    json.dump(instances, json_file, ensure_ascii=False, indent=4)