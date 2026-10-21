from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="Enterprise Business API",
    description="本章使用的模拟企业业务系统",
    version="1.0.0",
)


# 模拟员工数据
EMPLOYEES = {
    "E1001": {
        "employee_id": "E1001",
        "name": "张伟",
        "department": "销售部",
        "position": "销售经理",
        "email": "zhangwei@example.com",
        "status": "在职",
    },
    "E1002": {
        "employee_id": "E1002",
        "name": "李雷",
        "department": "研发部",
        "position": "后端开发工程师",
        "email": "lilei@example.com",
        "status": "在职",
    },
}


# 模拟订单数据
ORDERS = {
    "ORD20261001": {
        "order_id": "ORD20261001",
        "customer": "星河科技",
        "product": "企业数据分析平台",
        "amount": 128000,
        "status": "已发货",
        "created_at": "2026-10-12",
    },
    "ORD20261002": {
        "order_id": "ORD20261002",
        "customer": "远山制造",
        "product": "智能业务管理系统",
        "amount": 86000,
        "status": "处理中",
        "created_at": "2026-10-15",
    },
}


# 模拟发票数据
INVOICES = {
    "INV202610001": {
        "invoice_id": "INV202610001",
        "supplier": "上海云启科技有限公司",
        "amount": 26800,
        "department": "研发部",
        "status": "待审核",
        "invoice_date": "2026-10-16",
    },
}


# 模拟部门预算
DEPARTMENT_BUDGETS = {
    "D001": {
        "department": "销售部",
        "total_budget": 500000,
        "used_budget": 218000,
        "remaining_budget": 282000,
    },
    "D002": {
        "department": "研发部",
        "total_budget": 800000,
        "used_budget": 516000,
        "remaining_budget": 284000,
    },
}


@app.get("/health")
def health_check():
    """检查企业业务系统是否正常运行。"""
    return {
        "status": "ok",
        "service": "enterprise-business-api",
    }


@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: str):
    """查询员工档案。"""
    employee = EMPLOYEES.get(employee_id)

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail=f"没有找到员工：{employee_id}",
        )

    return employee


@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    """查询订单信息。"""
    order = ORDERS.get(order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail=f"没有找到订单：{order_id}",
        )

    return order


@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    """查询发票详情。"""
    invoice = INVOICES.get(invoice_id)

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail=f"没有找到发票：{invoice_id}",
        )

    return invoice


@app.get("/api/departments/{department}/budget")
def get_department_budget(department: str):
    """查询部门预算。"""
    budget = DEPARTMENT_BUDGETS.get(department)

    if budget is None:
        raise HTTPException(
            status_code=404,
            detail=f"没有找到部门预算：{department}",
        )

    return budget