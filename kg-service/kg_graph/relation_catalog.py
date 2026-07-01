from __future__ import annotations

from typing import Any

GENERIC_RELATION_TEMPLATES: tuple[dict[str, Any], ...] = (
    {"relation_key": "cooperate_with", "relation_label": "合作", "aliases": ("合作", "战略合作", "共建")},
    {"relation_key": "competes_with", "relation_label": "竞争", "aliases": ("竞争", "竞品", "对手", "同业竞争")},
    {"relation_key": "supplies_to", "relation_label": "供应", "aliases": ("供应", "供货", "配套", "供给")},
    {"relation_key": "customer_of", "relation_label": "客户", "aliases": ("客户", "采购", "购买", "下游客户")},
    {"relation_key": "invests_in", "relation_label": "投资", "aliases": ("投资", "参股", "入股", "控股")},
    {"relation_key": "acquires", "relation_label": "并购", "aliases": ("并购", "收购", "兼并")},
    {"relation_key": "joint_venture", "relation_label": "合资", "aliases": ("合资", "合营")},
    {"relation_key": "channel_partner", "relation_label": "代理/渠道", "aliases": ("代理", "渠道", "经销", "分销")},
    {"relation_key": "rd_collaboration", "relation_label": "研发合作", "aliases": ("研发合作", "联合研发", "共同研发")},
)

INDUSTRY_RELATION_TEMPLATES: dict[str, tuple[dict[str, Any], ...]] = {
    "semiconductor": (
        {"relation_key": "wafer_foundry", "relation_label": "晶圆代工", "aliases": ("晶圆代工", "代工制造", "foundry")},
        {"relation_key": "packaging_testing_service", "relation_label": "封测服务", "aliases": ("封测", "封装测试")},
        {"relation_key": "eda_ip_license", "relation_label": "EDA/IP授权", "aliases": ("EDA", "IP授权", "IP许可")},
        {"relation_key": "semiconductor_equipment_supply", "relation_label": "设备供应", "aliases": ("半导体设备", "设备供应")},
        {"relation_key": "semiconductor_material_supply", "relation_label": "材料供应", "aliases": ("半导体材料", "材料供应")},
        {"relation_key": "capacity_cooperation", "relation_label": "产能合作", "aliases": ("产能合作", "产能保障")},
        {"relation_key": "process_platform_cooperation", "relation_label": "工艺平台合作", "aliases": ("工艺平台", "制程合作")},
    ),
    "new_energy": (
        {"relation_key": "vehicle_battery_supply", "relation_label": "动力电池配套", "aliases": ("动力电池配套", "电池配套", "动力电池供应")},
        {"relation_key": "new_energy_material_supply", "relation_label": "材料供应", "aliases": ("锂电材料", "正极材料", "负极材料", "电解液", "材料供应")},
        {"relation_key": "module_supply", "relation_label": "组件供应", "aliases": ("组件供应", "光伏组件")},
        {"relation_key": "energy_storage_integration", "relation_label": "储能集成", "aliases": ("储能集成", "储能系统")},
        {"relation_key": "vehicle_matching", "relation_label": "整车配套", "aliases": ("整车配套", "车型配套")},
        {"relation_key": "grid_connection", "relation_label": "电网接入", "aliases": ("电网接入", "并网")},
        {"relation_key": "epc_project_cooperation", "relation_label": "EPC/项目合作", "aliases": ("EPC", "项目合作", "工程总包")},
    ),
    "pharma": (
        {"relation_key": "cxo_service", "relation_label": "CRO/CDMO服务", "aliases": ("CRO", "CDMO", "CXO", "研发外包", "生产外包")},
        {"relation_key": "license_in_out", "relation_label": "License-in/out", "aliases": ("License", "授权引进", "对外授权")},
        {"relation_key": "pipeline_collaboration", "relation_label": "管线合作", "aliases": ("管线合作", "联合开发药物")},
        {"relation_key": "commercialization_partner", "relation_label": "商业化合作", "aliases": ("商业化", "推广合作", "销售合作")},
        {"relation_key": "api_supply", "relation_label": "原料药供应", "aliases": ("原料药", "API供应")},
        {"relation_key": "drug_distribution", "relation_label": "药品流通", "aliases": ("药品流通", "配送", "分销")},
        {"relation_key": "clinical_trial_collaboration", "relation_label": "临床试验合作", "aliases": ("临床试验", "临床合作")},
    ),
    "automotive": (
        {"relation_key": "oem_supplier", "relation_label": "主机厂-供应商", "aliases": ("主机厂", "供应商", "定点")},
        {"relation_key": "tier1_supply", "relation_label": "Tier1配套", "aliases": ("Tier1", "一级供应商", "一级配套")},
        {"relation_key": "automotive_battery_supply", "relation_label": "动力电池配套", "aliases": ("动力电池配套", "电池供应")},
        {"relation_key": "intelligent_driving_solution", "relation_label": "智能驾驶方案", "aliases": ("智能驾驶", "自动驾驶方案", "ADAS")},
        {"relation_key": "automotive_chip_supply", "relation_label": "车规芯片供应", "aliases": ("车规芯片", "汽车芯片")},
        {"relation_key": "platform_cooperation", "relation_label": "平台合作", "aliases": ("平台合作", "车型平台")},
        {"relation_key": "aftermarket_channel", "relation_label": "后市场渠道", "aliases": ("后市场", "维修渠道", "服务渠道")},
    ),
}


def match_relation_template(relation_text: str, profile_id: str = "generic") -> dict[str, str]:
    text = str(relation_text or "").strip()
    for template in INDUSTRY_RELATION_TEMPLATES.get(profile_id, ()):
        if _matches(text, template):
            return _matched(template, "industry_template")
    for template in GENERIC_RELATION_TEMPLATES:
        if _matches(text, template):
            return _matched(template, "generic")
    return {
        "relation_key": "special_relation",
        "relation_label": text or "特殊关系",
        "relation_level": "special",
    }


def build_relation_prompt_hint(profile_id: str = "generic") -> str:
    generic = "、".join(template["relation_label"] for template in GENERIC_RELATION_TEMPLATES)
    industry_templates = INDUSTRY_RELATION_TEMPLATES.get(profile_id, ())
    industry = "、".join(template["relation_label"] for template in industry_templates) or "无内置行业模板"
    industry_title = _profile_title(profile_id)
    return (
        f"通用关系：{generic}。\n"
        f"{industry_title}行业关系：{industry}。\n"
        "特殊关系：如果证据中的公司关系不属于通用关系，也不属于当前行业关系，请标记为 special，"
        "关系名称用证据中的业务语义命名，并写清解释。"
    )


def _matches(text: str, template: dict[str, Any]) -> bool:
    return any(alias.lower() in text.lower() for alias in template.get("aliases", ()))


def _matched(template: dict[str, Any], level: str) -> dict[str, str]:
    return {
        "relation_key": str(template["relation_key"]),
        "relation_label": str(template["relation_label"]),
        "relation_level": level,
    }


def _profile_title(profile_id: str) -> str:
    return {
        "semiconductor": "半导体",
        "new_energy": "新能源",
        "pharma": "医药",
        "automotive": "汽车",
    }.get(profile_id, "当前")
