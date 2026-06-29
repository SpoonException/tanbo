"""对应 JS 中 uploadDMFile 的 Python 实现"""

import json
import requests

from totallink import config

# ===== 配置（请替换为你的实际地址和 token） =====
BASE_URL = "http://124.71.144.80:8081"


def upload_dm_file(code, num, type_, RDs, file_path, para, headers=None):
    """
    上传文件
    :param code:      dmCode
    :param num:       dmNum
    :param type_:     scriptType（添加/编辑记录）
    :param RDs:       关联记录 ID 列表
    :param file_path: 本地文件路径
    :param para:      Para 参数
    :param headers:   额外的请求头（如 token 放 Header 时使用）
    """
    # 构建请求体
    data = {
        "loginID": config.loginID,
        "par": {
            "dm": {
                "dmCode": code,
                "dmNum": num,
                "Para": para
            },
            "scriptType": type_,
            "rowData": RDs
        }
    }
    print("请求数据:", json.dumps(data, ensure_ascii=False, indent=2))

    # 打开文件并构造 multipart/form-data
    with open(file_path, "rb") as f:
        files = {
            "para": (None, json.dumps(data)),
            "file": f,
        }
        response = requests.post(
            url=f"{config.api_base_url}/DataModel/linkDMFileUpload",
            files=files,
            headers=headers or {},
        )

    print("状态码:", response.status_code)
    try:
        print("响应:", response.json())
    except Exception:
        print("响应:", response.text)
    return response


if __name__ == "__main__":
    # ===== 调用示例（请替换为真实参数） =====
    resp = upload_dm_file(
        code="LINKFLOW",
        num="25",
        type_="1",
        RDs={"DOCNUM": "APS0000000295", "LINKUPLOADGROUP": "Artisan"},
        file_path="../chenming.pdf",
        para=["APS0000000295", "2"],
    )
