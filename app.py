import streamlit as st
import pandas as pd
import requests
import re
import io
import json
import sys
import traceback
from database import init_db, verify_password  # 导入数据库初始化和验证函数

# 在应用标题之前检查openpyxl状态，确保状态信息最先显示
st.sidebar.title("环境状态")

# 检查是否有openpyxl模块
try:
    import openpyxl
    from openpyxl import Workbook
    EXCEL_EXPORT_AVAILABLE = True
    excel_version = openpyxl.__version__
    st.sidebar.success(f"✅ openpyxl模块已加载: 版本 {excel_version}")
except ImportError as e:
    EXCEL_EXPORT_AVAILABLE = False
    st.sidebar.error(f"❌ 无法导入openpyxl模块: {str(e)}")
    st.sidebar.info("您可以通过运行 'pip install openpyxl' 来安装此模块")
except Exception as e:
    EXCEL_EXPORT_AVAILABLE = False
    st.sidebar.error(f"❌ 加载openpyxl模块时出现未知错误: {str(e)}")
    st.sidebar.info("Python路径: " + ", ".join(sys.path))

# 显示Python环境信息
st.sidebar.subheader("Python环境")
st.sidebar.info(f"Python版本: {sys.version}")
st.sidebar.info(f"Pandas版本: {pd.__version__}")

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
    results = []  # 存储所有实例的关机结果
    success_count = 0
    fail_count = 0
    
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
        
        # 解析响应结果
        status = "成功"
        error_msg = ""
        request_id = ""
        full_response = json.dumps(response_json, ensure_ascii=False, indent=2)
        
        if 'data' in response_json and 'Response' in response_json['data']:
            request_id = response_json['data']['Response'].get('RequestId', '')
            if 'Error' in response_json['data']['Response']:
                status = "失败"
                error_msg = response_json['data']['Response']['Error'].get('Message', '未知错误')
                fail_count += 1
            else:
                success_count += 1
        else:
            status = "失败"
            error_msg = "无效的响应格式"
            fail_count += 1
        
        # 记录结果
        results.append({
            "实例ID": instance_id,
            "状态": status,
            "错误信息": error_msg,
            "请求ID": request_id,
            "时间": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 在界面显示详细信息
        st.subheader(f"实例 {instance_id} 关机请求结果")
        st.write(f"状态: {status}")
        st.write(f"请求ID: {request_id}")
        if error_msg:
            st.error(f"错误信息: {error_msg}")
        st.json(full_response)
    
    # 创建结果DataFrame
    results_df = pd.DataFrame(results)
    
    # 在界面上显示结果统计
    st.subheader("关机操作结果统计")
    st.write(f"总计: {len(instance_ids)} 台实例")
    st.write(f"成功: {success_count} 台")
    st.write(f"失败: {fail_count} 台")
    
    # 显示详细结果表格
    st.subheader("详细结果")
    st.dataframe(results_df)
    
    # 提供CSV下载
    csv = results_df.to_csv(index=False)
    st.download_button(
        label="下载关机结果报告(CSV)",
        data=csv,
        file_name=f"关机结果_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    # 提供Excel下载，如果支持的话
    if EXCEL_EXPORT_AVAILABLE:
        try:
            excel_buffer = io.BytesIO()
            results_df.to_excel(excel_buffer, engine='openpyxl', index=False, sheet_name="关机结果")
            excel_data = excel_buffer.getvalue()
            
            st.download_button(
                label="下载关机结果报告(Excel)",
                data=excel_data,
                file_name=f"关机结果_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Excel导出错误: {str(e)}")
            st.info("错误类型: " + str(type(e).__name__))
            st.code(traceback.format_exc())
            st.warning("请使用CSV格式导出，或者检查openpyxl安装。")
    else:
        st.info("Excel导出功能不可用。请确保openpyxl库已正确安装且可被当前Python环境访问。")
    
    return results_df

# 发送开机请求的函数
def start_instances(instance_ids, cookie, csrfcode, region, uin):
    results = []  # 存储所有实例的开机结果
    success_count = 0
    fail_count = 0
    
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
        
        # 解析响应结果
        status = "成功"
        error_msg = ""
        request_id = ""
        full_response = json.dumps(response_json, ensure_ascii=False, indent=2)
        
        if 'data' in response_json and 'Response' in response_json['data']:
            request_id = response_json['data']['Response'].get('RequestId', '')
            if 'Error' in response_json['data']['Response']:
                status = "失败"
                error_msg = response_json['data']['Response']['Error'].get('Message', '未知错误')
                fail_count += 1
            else:
                success_count += 1
        else:
            status = "失败"
            error_msg = "无效的响应格式"
            fail_count += 1
        
        # 记录结果
        results.append({
            "实例ID": instance_id,
            "状态": status,
            "错误信息": error_msg,
            "请求ID": request_id,
            "时间": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 在界面显示详细信息
        st.subheader(f"实例 {instance_id} 开机请求结果")
        st.write(f"状态: {status}")
        st.write(f"请求ID: {request_id}")
        if error_msg:
            st.error(f"错误信息: {error_msg}")
        st.json(full_response)
    
    # 创建结果DataFrame
    results_df = pd.DataFrame(results)
    
    # 在界面上显示结果统计
    st.subheader("开机操作结果统计")
    st.write(f"总计: {len(instance_ids)} 台实例")
    st.write(f"成功: {success_count} 台")
    st.write(f"失败: {fail_count} 台")
    
    # 显示详细结果表格
    st.subheader("详细结果")
    st.dataframe(results_df)
    
    # 提供CSV下载
    csv = results_df.to_csv(index=False)
    st.download_button(
        label="下载开机结果报告(CSV)",
        data=csv,
        file_name=f"开机结果_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    # 提供Excel下载，如果支持的话
    if EXCEL_EXPORT_AVAILABLE:
        try:
            excel_buffer = io.BytesIO()
            results_df.to_excel(excel_buffer, engine='openpyxl', index=False, sheet_name="开机结果")
            excel_data = excel_buffer.getvalue()
            
            st.download_button(
                label="下载开机结果报告(Excel)",
                data=excel_data,
                file_name=f"开机结果_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Excel导出错误: {str(e)}")
            st.info("错误类型: " + str(type(e).__name__))
            st.code(traceback.format_exc())
            st.warning("请使用CSV格式导出，或者检查openpyxl安装。")
    else:
        st.info("Excel导出功能不可用。请确保openpyxl库已正确安装且可被当前Python环境访问。")
    
    return results_df

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
        
        # 显示详细信息
        st.subheader(f"为实例 {instance_id} 创建镜像结果")
        st.json(json.dumps(response_json, ensure_ascii=False, indent=2))
        
        # 提取 ImageId 并添加到列表
        if 'data' in response_json and 'Response' in response_json['data']:
            image_id = response_json['data']['Response'].get('ImageId')
            if image_id:
                image_ids.append({'InstanceId': instance_id, 'ImageId': image_id})
                st.success(f"成功创建镜像，ImageId: {image_id}")
            else:
                st.error("未获取到 ImageId")
        else:
            st.error("响应格式无效")

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
        
        # 显示详细信息
        st.subheader(f"删除镜像 {image_id} 结果")
        st.json(json.dumps(response_json, ensure_ascii=False, indent=2))
        
        if 'data' in response_json and 'Response' in response_json['data']:
            if 'Error' in response_json['data']['Response']:
                st.error(f"删除失败: {response_json['data']['Response']['Error'].get('Message', '未知错误')}")
            else:
                st.success("删除成功")

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
        
        # 显示详细信息
        st.subheader(f"为磁盘 {disk_id} 创建快照结果")
        st.json(json.dumps(response_json, ensure_ascii=False, indent=2))
        
        # 提取 SnapshotId 并添加到列表
        if 'data' in response_json and 'Response' in response_json['data']:
            snapshot_id = response_json['data']['Response'].get('SnapshotId')
            if snapshot_id:
                snapshot_info.append({'DiskId': disk_id, 'SnapshotId': snapshot_id})
                st.success(f"成功创建快照，SnapshotId: {snapshot_id}")
            else:
                st.error("未获取到 SnapshotId")
        else:
            st.error("响应格式无效")

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
        
        # 显示详细信息
        st.subheader(f"删除快照 {snapshot_id} 结果")
        st.json(json.dumps(response_json, ensure_ascii=False, indent=2))
        
        if 'data' in response_json and 'Response' in response_json['data']:
            if 'Error' in response_json['data']['Response']:
                st.error(f"删除失败: {response_json['data']['Response']['Error'].get('Message', '未知错误')}")
            else:
                st.success("删除成功")

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
        results_df = stop_instances(data['ID_cvm'].unique(), cookie, csrfcode, region, uin)
        # 将结果保存到会话状态，以便可能的后续使用
        st.session_state.last_stop_results = results_df
    if st.button("执行开机"):
        results_df = start_instances(data['ID_cvm'].unique(), cookie, csrfcode, region, uin)
        # 将结果保存到会话状态，以便可能的后续使用
        st.session_state.last_start_results = results_df
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