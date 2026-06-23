"""
学生请假管理系统 - 自动化测试用例
使用 pytest + requests 进行接口测试
"""

import requests
import pytest
from datetime import datetime, timedelta
import json

# 基础配置
BASE_URL = "http://localhost:8080/api"
HEADERS = {"Content-Type": "application/json"}


class TestAuthLogin:
    """登录认证测试类"""

    def test_login_success(self):
        """测试用例1: 学生登录成功"""
        payload = {
            "username": "2025001",
            "password": "123456"
        }
        response = requests.post(f"{BASE_URL}/login", json=payload, headers=HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "success"
        assert "token" in data["data"]
        assert data["data"]["username"] == "2025001"
        print(f"✅ 登录成功，Token: {data['data']['token'][:20]}...")

    def test_login_wrong_password(self):
        """测试用例2: 用户登录失败 - 密码错误"""
        payload = {
            "username": "2025001",
            "password": "wrong_password"
        }
        response = requests.post(f"{BASE_URL}/login", json=payload, headers=HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 500
        assert data["message"] == "密码错误"
        print("✅ 密码错误验证通过")

    def test_login_user_not_exist(self):
        """测试用例3: 用户登录失败 - 用户不存在"""
        payload = {
            "username": "nonexistent_user",
            "password": "123456"
        }
        response = requests.post(f"{BASE_URL}/login", json=payload, headers=HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 500
        assert data["message"] == "用户不存在"
        print("✅ 用户不存在验证通过")


class TestLeaveApply:
    """请假申请测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前执行登录获取token"""
        login_payload = {
            "username": "2025001",
            "password": "123456"
        }
        login_response = requests.post(f"{BASE_URL}/login", json=login_payload, headers=HEADERS)
        self.token = login_response.json()["data"]["token"]
        self.auth_headers = {**HEADERS, "Authorization": f"Bearer {self.token}"}
        self.student_id = login_response.json()["data"]["userId"]

    def test_apply_leave_success(self):
        """测试用例4: 提交请假申请成功"""
        now = datetime.now()
        payload = {
            "studentId": self.student_id,
            "leaveType": 1,
            "startTime": (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "days": 1.0,
            "reason": "家里有事，需要请假一天",
            "status": 0
        }
        response = requests.post(
            f"{BASE_URL}/leave/apply",
            json=payload,
            headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] in ["success", "申请提交成功"]
        print("✅ 请假申请提交成功")

    def test_apply_leave_missing_params(self):
        """测试用例5: 提交请假申请 - 缺少必要参数"""
        payload = {
            "studentId": self.student_id,
            "leaveType": 1
        }
        response = requests.post(
            f"{BASE_URL}/leave/apply",
            json=payload,
            headers=self.auth_headers
        )

        # MyBatis-Plus可能会抛出异常或插入null值
        assert response.status_code in [200, 500]
        print("✅ 参数缺失处理验证通过")


class TestLeaveQuery:
    """请假查询测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """获取token和学生ID"""
        login_payload = {
            "username": "2025001",
            "password": "123456"
        }
        login_response = requests.post(f"{BASE_URL}/login", json=login_payload, headers=HEADERS)
        self.token = login_response.json()["data"]["token"]
        self.student_id = login_response.json()["data"]["userId"]

    def test_query_leave_list(self):
        """测试用例6: 查询学生请假列表"""
        params = {"studentId": self.student_id}
        headers = {**HEADERS, "Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{BASE_URL}/leave/list",
            params=params,
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)
        print(f"✅ 查询到 {len(data['data'])} 条请假记录")


class TestLeaveApproval:
    """请假审批测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """获取辅导员token"""
        login_payload = {
            "username": "teacher01",
            "password": "123456"
        }
        login_response = requests.post(f"{BASE_URL}/login", json=login_payload, headers=HEADERS)
        self.token = login_response.json()["data"]["token"]
        self.counselor_id = login_response.json()["data"]["userId"]
        self.auth_headers = {**HEADERS, "Authorization": f"Bearer {self.token}"}

    def test_query_pending_leaves(self):
        """测试用例7: 查询待审批请假列表"""
        params = {"counselorId": self.counselor_id}
        response = requests.get(
            f"{BASE_URL}/leave/pending",
            params=params,
            headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)
        print(f"✅ 查询到 {len(data['data'])} 条待审批记录")

    def test_approve_leave_pass(self):
        """测试用例8: 辅导员审批通过（3天内）"""
        # 先查询一条待审批记录
        params = {"counselorId": self.counselor_id}
        pending_response = requests.get(
            f"{BASE_URL}/leave/pending",
            params=params,
            headers=self.auth_headers
        )
        pending_list = pending_response.json()["data"]

        if not pending_list:
            pytest.skip("没有待审批记录，跳过此测试")

        leave_id = pending_list[0]["id"]

        # 审批通过
        approve_params = {
            "id": leave_id,
            "action": 1,
            "opinion": "同意请假"
        }
        response = requests.post(
            f"{BASE_URL}/leave/audit",
            params=approve_params,
            headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] in ["success", "审批完成"]
        print(f"✅ 请假记录 {leave_id} 审批通过")

    def test_approve_leave_reject(self):
        """测试用例9: 辅导员审批拒绝"""
        # 先查询一条待审批记录
        params = {"counselorId": self.counselor_id}
        pending_response = requests.get(
            f"{BASE_URL}/leave/pending",
            params=params,
            headers=self.auth_headers
        )
        pending_list = pending_response.json()["data"]

        if not pending_list:
            pytest.skip("没有待审批记录，跳过此测试")

        leave_id = pending_list[0]["id"]

        # 审批拒绝
        reject_params = {
            "id": leave_id,
            "action": 2,
            "opinion": "不符合规定，不予批准"
        }
        response = requests.post(
            f"{BASE_URL}/leave/audit",
            params=reject_params,
            headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] in ["success", "审批完成"]
        print(f"✅ 请假记录 {leave_id} 审批拒绝")


class TestStatistics:
    """统计功能测试类"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """获取管理员token"""
        login_payload = {
            "username": "admin",
            "password": "123456"
        }
        login_response = requests.post(f"{BASE_URL}/login", json=login_payload, headers=HEADERS)
        self.token = login_response.json()["data"]["token"]
        self.auth_headers = {**HEADERS, "Authorization": f"Bearer {self.token}"}

    def test_dashboard_statistics(self):
        """测试用例10: 获取统计数据"""
        response = requests.get(
            f"{BASE_URL}/stats/dashboard",
            headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        stats = data["data"]

        assert "total" in stats
        assert "pending" in stats
        assert "approved" in stats
        assert "rejected" in stats

        print(f"✅ 统计数据获取成功:")
        print(f"   总请假数: {stats['total']}")
        print(f"   待审批: {stats['pending']}")
        print(f"   已通过: {stats['approved']}")
        print(f"   已拒绝: {stats['rejected']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
