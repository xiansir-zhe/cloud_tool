import streamlit as st
import pandas as pd
import requests
import re
import io
import json
from database import init_db, verify_password  # 导入数据库初始化和验证函数

# 初始化数据库
init_db()

# 读取CSV文件
def load_instance_data(file_path):
    df = pd.read_csv(file_path)
    return df

# 从请求中提取cookie
def extract_cookie(request_text):
    # 尝试从 -H 'cookie: ...' 格式提取
    match = re.search(r"-H 'cookie: ([^']*)'", request_text)
    if match:
        return match.group(1)
    
    # 尝试从 -b '...' 格式提取
    match = re.search(r"-b '([^']*)'", request_text)
    if match:
        return match.group(1)
    
    return ''

# 从请求中提取x-csrfcode
def extract_csrfcode(request_text):
    match = re.search(r"-H 'x-csrfcode: ([^']*)'", request_text)
    return match.group(1) if match else ''

# 构建请求头
def build_headers(cookie, csrfcode):
    return {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cache-control': 'no-cache',
        'content-type': 'application/json; charset=UTF-8',
        'cookie': cookie,
        'origin': 'https://console.cloud.tencent.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://console.cloud.tencent.com/cvm/instance/index',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'x-csrfcode': csrfcode,
    }

# 通用请求函数
def send_request(action, data, cookie, csrfcode, uin, region=None):
    if region:
        url = f'https://workbench.cloud.tencent.com/cgi/capi?i=cvm/{action}&uin={uin}&region={region}'
    else:
        url = f'https://capi.cloud.tencent.com/cgi/capi?i=cbs/{action}&uin={uin}'
    headers = build_headers(cookie, csrfcode)
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 发送关机请求的函数
def stop_instances(instance_ids, cookie, csrfcode, region, uin):
    for instance_id in instance_ids:
        data = {
            "serviceType": "cvm",
            "action": "StopInstances",
            "data": {
                "Version": "2017-03-12",
                "InstanceIds": [instance_id],
                "StopType": "SOFT_FIRST",
                "StoppedMode": "KEEP_CHARGING"
            },
            "region": region
        }
        response_json = send_request("StopInstances", data, cookie, csrfcode, uin, region)
        st.write(f"Instance {instance_id} stop response: {response_json}")

# 发送开机请求的函数
def start_instances(instance_ids, cookie, csrfcode, region, uin):
    for instance_id in instance_ids:
        data = {
            "serviceType": "cvm",
            "action": "StartInstances",
            "data": {
                "Version": "2017-03-12",
                "InstanceIds": [instance_id]
            },
            "region": region
        }
        response_json = send_request("StartInstances", data, cookie, csrfcode, uin, region)
        st.write(f"Instance {instance_id} start response: {response_json}")

# 发送创建镜像请求的函数
def create_images(data, cookie, csrfcode, region, uin):
    image_ids = []  # 用于存储 ImageId 的列表
    for instance_id, group in data.groupby('ID_cvm'):
        image_name = group['cvm_name'].iloc[0] + '-image'
        data_disk_ids = group['ID_dataDisk'].tolist()
        data = {
            "serviceType": "cvm",
            "action": "CreateImage",
            "region": region,
            "data": {
                "Version": "2017-03-12",
                "InstanceId": instance_id,
                "ImageName": image_name,
                "ImageDescription": "CDC迁移",
                "ForcePoweroff": "FALSE",
                "Sysprep": "FALSE",
                "DataDiskIds": data_disk_ids
            }
        }
        response_json = send_request("CreateImage", data, cookie, csrfcode, uin, region)
        st.write(f"Create image for instance {instance_id} response: {response_json}")
        
        # 提取 ImageId 并添加到列表
        if 'data' in response_json and 'Response' in response_json['data']:
            image_id = response_json['data']['Response'].get('ImageId')
            if image_id:
                image_ids.append({'InstanceId': instance_id, 'ImageId': image_id})

    # 将 ImageId 列表转换为 DataFrame
    if image_ids:
        df_image_ids = pd.DataFrame(image_ids)
        # 将 DataFrame 转换为 CSV
        csv = df_image_ids.to_csv(index=False)
        # 使用 Streamlit 提供下载链接
        st.download_button(
            label="下载 ImageId CSV",
            data=csv,
            file_name='image_ids.csv',
            mime='text/csv'
        )

# 发送删除镜像请求的函数
def delete_images(image_ids, cookie, csrfcode, region, uin):
    for image_id in image_ids:
        data = {
            "serviceType": "cvm",
            "action": "DeleteImages",
            "region": region,
            "data": {
                "Version": "2017-03-12",
                "ImageIds": [image_id],
                "DeleteBindedSnap": True
            }
        }
        response_json = send_request("DeleteImages", data, cookie, csrfcode, uin, region)
        st.write(f"Delete image {image_id} response: {response_json}")

# 发送创建快照请求的函数
def create_snapshots(disk_data, cookie, csrfcode, uin):
    snapshot_info = []  # 用于存储成功创建的快照信息
    for index, row in disk_data.iterrows():
        disk_id = row['ID']
        snapshot_name = f"{row['ID']}_last_snapshot"
        data = {
            "serviceType": "cbs",
            "action": "CreateSnapshot",
            "regionId": 4,  # 根据需要调整 regionId
            "data": {
                "Version": "2017-03-12",
                "DiskId": disk_id,
                "SnapshotName": snapshot_name
            }
        }
        response_json = send_request("CreateSnapshot", data, cookie, csrfcode, uin)
        st.write(f"Create snapshot for disk {disk_id} response: {response_json}")
        
        # 提取 SnapshotId 并添加到列表
        if 'data' in response_json and 'Response' in response_json['data']:
            snapshot_id = response_json['data']['Response'].get('SnapshotId')
            if snapshot_id:
                snapshot_info.append({'DiskId': disk_id, 'SnapshotId': snapshot_id})

    # 将 Snapshot 信息列表转换为 DataFrame
    if snapshot_info:
        df_snapshot_info = pd.DataFrame(snapshot_info)
        # 将 DataFrame 转换为 CSV
        csv = df_snapshot_info.to_csv(index=False)
        # 使用 Streamlit 提供下载链接
        st.download_button(
            label="下载 Snapshot 信息 CSV",
            data=csv,
            file_name='snapshot_info.csv',
            mime='text/csv'
        )

# 发送删除快照请求的函数
def delete_snapshots(snapshot_data, cookie, csrfcode, uin):
    for index, row in snapshot_data.iterrows():
        snapshot_id = row['SnapshotId']
        data = {
            "serviceType": "cbs",
            "action": "DeleteSnapshots",
            "regionId": 4,  # 根据需要调整 regionId
            "data": {
                "Version": "2017-03-12",
                "SnapshotIds": [snapshot_id]
            }
        }
        response_json = send_request("DeleteSnapshots", data, cookie, csrfcode, uin)
        st.write(f"Delete snapshot {snapshot_id} response: {response_json}")

# Streamlit界面
st.title("批量开关机、创建镜像和快照程序")

# 添加使用说明
with st.expander("📋 使用说明", expanded=True):
    st.markdown("""
    ### 文件上传要求

    #### 1. 批量开关机文件 (CSV格式)
    - 必须包含以下字段：
        - `ID_cvm`: 云服务器实例ID（例如：ins-xxxxxx）
    - 示例格式：
        ```
        ID_cvm
        ins-xxxxxx
        ins-yyyyyy
        ```

    #### 2. 批量创建镜像文件 (CSV格式)
    - 必须包含以下字段：
        - `ID_cvm`: 云服务器实例ID（例如：ins-xxxxxx）
        - `cvm_name`: 云服务器名称（例如：test-server）
        - `ID_dataDisk`: 数据盘ID（例如：disk-xxxxxx）
    - 示例格式：
        ```
        ID_cvm,cvm_name,ID_dataDisk
        ins-xxxxxx,test-server,disk-xxxxxx
        ins-yyyyyy,prod-server,disk-yyyyyy
        ```

    #### 3. 批量删除镜像文件 (CSV格式)
    - 必须包含以下字段：
        - `ImageId`: 镜像ID（例如：img-xxxxxx）
    - 示例格式：
        ```
        ImageId
        img-xxxxxx
        img-yyyyyy
        ```

    #### 4. 批量创建快照文件 (CSV格式)
    - 必须包含以下字段：
        - `ID`: 云硬盘ID（例如：disk-xxxxxx）
    - 示例格式：
        ```
        ID
        disk-xxxxxx
        disk-yyyyyy
        ```

    #### 5. 批量删除快照文件 (CSV格式)
    - 必须包含以下字段：
        - `SnapshotId`: 快照ID（例如：snap-xxxxxx）
    - 示例格式：
        ```
        SnapshotId
        snap-xxxxxx
        snap-yyyyyy
        ```

    ### 注意事项
    1. 所有CSV文件必须使用UTF-8编码保存
    2. 字段名称必须完全匹配上述要求，区分大小写
    3. 删除操作需要输入正确的密码（安全措施）
    4. 请确保所有ID都是有效的腾讯云资源ID
    5. 批量开关机操作只需要云服务器实例ID，而创建镜像操作需要额外的云服务器名称和数据盘ID信息
    
    ### 操作流程
    1. 输入完整的请求信息以提取Cookie和CSRF代码
    2. 输入UIN和区域信息
    3. 上传相应的CSV文件
    4. 点击对应的操作按钮执行批量操作
    """)

# 输入完整的请求信息
request_text = st.text_area("输入完整的请求信息以更新Cookie和CSRF代码", height=200)
cookie = extract_cookie(request_text)
csrfcode = extract_csrfcode(request_text)
st.write(f"提取的Cookie: {cookie}")
st.write(f"提取的CSRF代码: {csrfcode}")

# 新增：输入 uin
uin = st.text_input("输入 UIN（例如：100038461096）", value="100038461096")

# 新增：输入 region
region = st.text_input("输入 region（例如：ap-hongkong）", value="ap-hongkong")

# 新增：输入密码
password = st.text_input("输入密码以进行删除操作", type="password")

uploaded_file = st.file_uploader("上传CSV文件用于批量开关机以及创建镜像", type="csv")

# 新增：上传包含 ImageId 的 CSV 文件
image_id_file = st.file_uploader("上传包含 ImageId 的 CSV 文件用于批量删除镜像", type="csv")

# 新增：上传包含 DiskID 和 名称 的 CSV 文件
snapshot_file = st.file_uploader("上传包含 DiskID 和 名称 的 CSV 文件用于批量创建快照", type="csv")

# 新增：上传包含 SnapshotId 的 CSV 文件
delete_snapshot_file = st.file_uploader("上传包含 SnapshotId 的 CSV 文件用于批量删除快照", type="csv")

if uploaded_file is not None:
    data = load_instance_data(uploaded_file)
    if st.button("执行关机"):
        stop_instances(data['ID_cvm'].unique(), cookie, csrfcode, region, uin)
    if st.button("执行开机"):
        start_instances(data['ID_cvm'].unique(), cookie, csrfcode, region, uin)
    if st.button("创建镜像"):
        create_images(data, cookie, csrfcode, region, uin)

# 新增：批量删除镜像
if image_id_file is not None:
    image_data = pd.read_csv(image_id_file)
    if st.button("批量删除镜像"):
        if verify_password(password):
            delete_images(image_data['ImageId'].tolist(), cookie, csrfcode, region, uin)
        else:
            st.error("密码错误，无法执行删除操作。")

# 新增：批量创建快照
if snapshot_file is not None:
    snapshot_data = pd.read_csv(snapshot_file)
    if st.button("批量创建快照"):
        create_snapshots(snapshot_data, cookie, csrfcode, uin)

# 新增：批量删除快照
if delete_snapshot_file is not None:
    delete_snapshot_data = pd.read_csv(delete_snapshot_file)
    if st.button("批量删除快照"):
        if verify_password(password):
            delete_snapshots(delete_snapshot_data, cookie, csrfcode, uin)
        else:
            st.error("密码错误，无法执行删除操作。") 