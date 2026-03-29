#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AEdu KB 闭环校验脚本
====================
用途：验证知识底座 (KB) 首发切片的最小闭环完整性
适用范围：安徽省/高中/高一/物理/PHY_PEP_G1_V1

校验维度：
1. Schema 校验 - JSON Schema 合规性
2. 冻结值校验 - 地区、教材版本等冻结值一致性
3. 引用完整性校验 - 章节/知识点/能力点/锚点之间的引用关系
4. 依赖关系校验 - 依赖链无环、方向正确

使用方式：
    python validate_kb_closure.py --data-dir ./samples --verbose
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


# ============== 冻结值常量 ==============
FROZEN_VALUES = {
    "region_id": "CN_AH",
    "curriculum_version_id": "PHY_PEP_G1_V1",
    "subject": "物理",
    "grade_level": "高一",
    "volume_no": "必修一",
    "root_node_id": "PHY_PEP_G1_V1_ROOT"
}

# ============== 校验结果数据结构 ==============
class ValidationResult:
    def __init__(self):
        self.passed = True
        self.p0_issues: List[Dict[str, Any]] = []  # 阻断项
        self.p1_issues: List[Dict[str, Any]] = []  # 高优先级
        self.p2_issues: List[Dict[str, Any]] = []  # 次要项
        self.summary: Dict[str, Any] = {}

    def add_issue(self, level: str, issue_type: str, description: str,
                  affected_objects: Optional[List[str]] = None,
                  suggested_action: Optional[str] = None):
        issue = {
            "issue_id": f"ISS_{len(self.p0_issues) + len(self.p1_issues) + len(self.p2_issues) + 1:03d}",
            "level": level,
            "type": issue_type,
            "description": description,
            "affected_objects": affected_objects or [],
            "suggested_action": suggested_action or "手动检查修复"
        }
        if level == "P0":
            self.p0_issues.append(issue)
            self.passed = False
        elif level == "P1":
            self.p1_issues.append(issue)
        else:
            self.p2_issues.append(issue)

    def to_report(self) -> Dict[str, Any]:
        return {
            "validation_id": f"VAL_KB_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "validation_type": "kb_closure",
            "validated_at": datetime.now().isoformat(),
            "frozen_values": FROZEN_VALUES,
            "result": "pass" if self.passed else "fail",
            "summary": self.summary,
            "issues": {
                "p0_count": len(self.p0_issues),
                "p1_count": len(self.p1_issues),
                "p2_count": len(self.p2_issues),
                "p0_issues": self.p0_issues,
                "p1_issues": self.p1_issues,
                "p2_issues": self.p2_issues
            }
        }


# ============== Schema 校验器 ==============
class SchemaValidator:
    """JSON Schema 校验器（简化版，不依赖外部库）"""

    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        self._validate_recursive(data, self.schema, "", errors)
        return len(errors) == 0, errors

    def _validate_recursive(self, data: Any, schema: Dict[str, Any], path: str, errors: List[str]):
        # 类型校验
        if "type" in schema:
            expected_type = schema["type"]
            if expected_type == "object" and not isinstance(data, dict):
                errors.append(f"{path}: 期望对象类型，得到 {type(data).__name__}")
                return
            elif expected_type == "array" and not isinstance(data, list):
                errors.append(f"{path}: 期望数组类型，得到 {type(data).__name__}")
                return
            elif expected_type == "string" and not isinstance(data, str):
                errors.append(f"{path}: 期望字符串类型，得到 {type(data).__name__}")
                return
            elif expected_type == "integer" and not isinstance(data, int):
                errors.append(f"{path}: 期望整数类型，得到 {type(data).__name__}")
                return
            elif expected_type == "boolean" and not isinstance(data, bool):
                errors.append(f"{path}: 期望布尔类型，得到 {type(data).__name__}")
                return

        # 必填字段校验
        if "required" in schema and isinstance(data, dict):
            for field in schema["required"]:
                if field not in data:
                    errors.append(f"{path}: 缺少必填字段 '{field}'")

        # 属性校验
        if "properties" in schema and isinstance(data, dict):
            for key, value in data.items():
                if key in schema["properties"]:
                    new_path = f"{path}.{key}" if path else key
                    self._validate_recursive(value, schema["properties"][key], new_path, errors)

        # const 校验（冻结值）
        if "const" in schema and data != schema["const"]:
            errors.append(f"{path}: 值应为 '{schema['const']}', 得到 '{data}'")

        # enum 校验
        if "enum" in schema and data not in schema["enum"]:
            errors.append(f"{path}: 值应在 {schema['enum']} 中，得到 '{data}'")

        # pattern 校验
        if "pattern" in schema and isinstance(data, str):
            import re
            if not re.match(schema["pattern"], data):
                errors.append(f"{path}: 值不匹配模式 '{schema['pattern']}', 得到 '{data}'")

        # minItems 校验
        if "minItems" in schema and isinstance(data, list):
            if len(data) < schema["minItems"]:
                errors.append(f"{path}: 数组长度应 >= {schema['minItems']}, 实际为 {len(data)}")

        # minLength 校验
        if "minLength" in schema and isinstance(data, str):
            if len(data) < schema["minLength"]:
                errors.append(f"{path}: 字符串长度应 >= {schema['minLength']}, 实际为 {len(data)}")


# ============== 主校验器 ==============
class KBClosureValidator:
    """KB 闭环校验主类"""

    def __init__(self, data_dir: str, verbose: bool = False):
        self.data_dir = Path(data_dir)
        self.verbose = verbose
        self.result = ValidationResult()
        self.data: Dict[str, Any] = {}
        self.schemas: Dict[str, Any] = {}

    def load_data(self) -> bool:
        """加载所有样例数据和 Schema"""
        files_to_load = [
            ("chapter_tree", "chapter_tree_sample.json"),
            ("knowledge", "knowledge_sample.json"),
            ("ability", "ability_sample.json"),
            ("anchor", "anchor_sample.json"),
            ("dependency", "dependency_sample.json"),
            ("end_to_end", "end_to_end_samples.json"),
        ]

        schemas_to_load = [
            ("chapter_tree", "chapter_tree_schema.json"),
            ("knowledge", "knowledge_schema.json"),
            ("ability", "ability_schema.json"),
            ("anchor", "anchor_schema.json"),
        ]

        all_loaded = True

        for key, filename in files_to_load:
            filepath = self.data_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.data[key] = json.load(f)
                if self.verbose:
                    print(f"[OK] 已加载数据：{filename}")
            else:
                self.result.add_issue(
                    "P0", "file_missing",
                    f"必需的数据文件不存在：{filename}",
                    [str(filepath)],
                    "确保文件存在于 samples 目录中"
                )
                all_loaded = False

        for key, filename in schemas_to_load:
            filepath = self.data_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.schemas[key] = json.load(f)
                if self.verbose:
                    print(f"[OK] 已加载 Schema: {filename}")
            else:
                self.result.add_issue(
                    "P0", "schema_missing",
                    f"必需的 Schema 文件不存在：{filename}",
                    [str(filepath)],
                    "确保 Schema 文件存在于 samples 目录中"
                )
                all_loaded = False

        return all_loaded

    def validate_frozen_values(self):
        """校验冻结值一致性"""
        if self.verbose:
            print("\n=== 校验冻结值 ===")

        for data_key, data in self.data.items():
            if "metadata" not in data:
                self.result.add_issue(
                    "P0", "metadata_missing",
                    f"{data_key} 缺少 metadata 字段",
                    [data_key],
                    "添加 metadata 字段并填写冻结值"
                )
                continue

            meta = data["metadata"]

            # 校验关键冻结值
            for field, expected in FROZEN_VALUES.items():
                if field in ["root_node_id"]:  # root_node_id 不在 metadata 中
                    continue
                if field not in meta:
                    # 某些数据可能没有所有字段，跳过
                    continue
                if meta[field] != expected:
                    self.result.add_issue(
                        "P0", "frozen_value_mismatch",
                        f"{data_key}.metadata.{field} 应为 '{expected}', 实际为 '{meta[field]}'",
                        [data_key],
                        f"修正 {field} 为冻结值 '{expected}'"
                    )

        if self.verbose:
            print("[OK] 冻结值校验完成")

    def validate_schema_compliance(self):
        """校验 JSON Schema 合规性"""
        if self.verbose:
            print("\n=== 校验 Schema 合规性 ===")

        for data_key, schema_key in [
            ("chapter_tree", "chapter_tree"),
            ("knowledge", "knowledge"),
            ("ability", "ability"),
            ("anchor", "anchor"),
        ]:
            if data_key not in self.data or schema_key not in self.schemas:
                continue

            data = self.data[data_key]
            schema = self.schemas[schema_key]

            validator = SchemaValidator(schema)
            is_valid, errors = validator.validate(data)

            if is_valid:
                if self.verbose:
                    print(f"[OK] {data_key} 通过 Schema 校验")
            else:
                for error in errors[:5]:  # 最多报告 5 个错误
                    self.result.add_issue(
                        "P0", "schema_violation",
                        f"{data_key} Schema 校验失败：{error}",
                        [data_key],
                        "根据 Schema 修正数据格式"
                    )

        if self.verbose:
            print("[OK] Schema 合规性校验完成")

    def validate_chapter_tree(self):
        """校验章节树完整性和关系"""
        if self.verbose:
            print("\n=== 校验章节树 ===")

        if "chapter_tree" not in self.data:
            return

        tree = self.data["chapter_tree"]["chapter_tree"]
        node_ids = {node["chapter_node_id"] for node in tree}

        # 检查是否有根节点
        root_nodes = [n for n in tree if n.get("parent_node_id") is None]
        if len(root_nodes) != 1:
            self.result.add_issue(
                "P0", "chapter_root_invalid",
                f"章节树应有 1 个根节点，实际有 {len(root_nodes)} 个",
                [n["chapter_node_id"] for n in root_nodes],
                "确保只有一个顶层节点（册级别）"
            )

        # 检查父子关系
        for node in tree:
            parent_id = node.get("parent_node_id")
            if parent_id and parent_id not in node_ids:
                self.result.add_issue(
                    "P0", "chapter_parent_missing",
                    f"节点 {node['chapter_node_id']} 的父节点 {parent_id} 不存在",
                    [node["chapter_node_id"]],
                    "添加缺失的父节点或修正 parent_node_id"
                )

        # 检查唯一性
        id_counts = {}
        for node in tree:
            nid = node["chapter_node_id"]
            id_counts[nid] = id_counts.get(nid, 0) + 1

        duplicates = [nid for nid, count in id_counts.items() if count > 1]
        if duplicates:
            self.result.add_issue(
                "P0", "chapter_id_duplicate",
                f"章节节点 ID 重复：{duplicates}",
                duplicates,
                "确保每个节点 ID 唯一"
            )

        if self.verbose:
            print(f"[OK] 章节树校验完成（共 {len(tree)} 个节点）")

    def validate_knowledge_references(self):
        """校验知识点引用完整性"""
        if self.verbose:
            print("\n=== 校验知识点引用 ===")

        if "knowledge" not in self.data or "chapter_tree" not in self.data:
            return

        knowledge = self.data["knowledge"]["knowledge_points"]
        chapter_nodes = {n["chapter_node_id"]: n for n in self.data["chapter_tree"]["chapter_tree"]}

        # 检查章节引用
        for kp in knowledge:
            chapter_id = kp.get("chapter_node_id")
            if chapter_id and chapter_id not in chapter_nodes:
                self.result.add_issue(
                    "P0", "knowledge_chapter_missing",
                    f"知识点 {kp['knowledge_id']} 引用的章节 {chapter_id} 不存在",
                    [kp["knowledge_id"]],
                    "修正 chapter_node_id 或添加缺失的章节"
                )

        # 检查能力点引用
        ability_ids = set()
        if "ability" in self.data:
            for ap in self.data["ability"]["ability_points"]:
                ability_ids.add(ap["ability_id"])

        for kp in knowledge:
            for ability_id in kp.get("ability_refs", []):
                if ability_id and ability_id not in ability_ids:
                    self.result.add_issue(
                        "P1", "knowledge_ability_missing",
                        f"知识点 {kp['knowledge_id']} 引用的能力点 {ability_id} 不存在",
                        [kp["knowledge_id"], ability_id],
                        "添加缺失的能力点或修正引用"
                    )

        if self.verbose:
            print(f"[OK] 知识点引用校验完成（共 {len(knowledge)} 个知识点）")

    def validate_anchor_references(self):
        """校验锚点引用完整性"""
        if self.verbose:
            print("\n=== 校验锚点引用 ===")

        if "anchor" not in self.data or "chapter_tree" not in self.data:
            return

        anchors = self.data["anchor"]["anchor_points"]
        chapter_nodes = {n["chapter_node_id"]: n for n in self.data["chapter_tree"]["chapter_tree"]}

        # 检查章节引用
        for anchor in anchors:
            chapter_id = anchor.get("chapter_node_id")
            if chapter_id and chapter_id not in chapter_nodes:
                self.result.add_issue(
                    "P0", "anchor_chapter_missing",
                    f"锚点 {anchor['anchor_id']} 引用的章节 {chapter_id} 不存在",
                    [anchor["anchor_id"]],
                    "修正 chapter_node_id 或添加缺失的章节"
                )

        if self.verbose:
            print(f"[OK] 锚点引用校验完成（共 {len(anchors)} 个锚点）")

    def validate_dependency_graph(self):
        """校验依赖关系图（无环检测）"""
        if self.verbose:
            print("\n=== 校验依赖关系 ===")

        if "dependency" not in self.data:
            return

        dependencies = self.data["dependency"]["dependencies"]

        # 构建依赖图
        graph: Dict[str, List[str]] = {}
        all_nodes = set()

        for dep in dependencies:
            from_id = dep["from_knowledge_id"]
            to_id = dep["to_knowledge_id"]
            all_nodes.add(from_id)
            all_nodes.add(to_id)

            if from_id not in graph:
                graph[from_id] = []
            graph[from_id].append(to_id)

        # DFS 检测环
        def has_cycle(node: str, visited: set, rec_stack: set) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        rec_stack = set()
        has_loop = False

        for node in all_nodes:
            if node not in visited:
                if has_cycle(node, visited, rec_stack):
                    has_loop = True
                    break

        if has_loop:
            self.result.add_issue(
                "P0", "dependency_cycle_detected",
                "依赖关系中存在循环依赖",
                list(all_nodes),
                "检查并打破依赖环"
            )
        else:
            if self.verbose:
                print("[OK] 依赖关系无环")

        if self.verbose:
            print(f"[OK] 依赖关系校验完成（共 {len(dependencies)} 条依赖）")

    def validate_audit_fields(self):
        """校验审计字段完整性"""
        if self.verbose:
            print("\n=== 校验审计字段 ===")

        required_audit_fields = ["created_by", "created_at", "updated_by", "updated_at"]

        # 校验 end_to_end_samples 的 audit_trail
        if "end_to_end" in self.data:
            audit_trail = self.data["end_to_end"].get("audit_trail", {})
            for field in required_audit_fields:
                if field not in audit_trail:
                    self.result.add_issue(
                        "P0", "audit_field_missing",
                        f"audit_trail 缺少必填字段：{field}",
                        ["audit_trail"],
                        f"添加 {field} 字段"
                    )

            # 校验 review_ticket_ref
            if "review_ticket_ref" not in audit_trail:
                self.result.add_issue(
                    "P0", "review_ticket_ref_missing",
                    "audit_trail 缺少 review_ticket_ref 字段",
                    ["audit_trail"],
                    "添加 review_ticket_ref 字段"
                )

            # 校验 kb_ref
            if "kb_ref" not in audit_trail:
                self.result.add_issue(
                    "P0", "kb_ref_missing",
                    "audit_trail 缺少 kb_ref 字段",
                    ["audit_trail"],
                    "添加 kb_ref 字段"
                )

            if self.verbose:
                print("[OK] 审计字段校验完成")

    def validate_end_to_end_samples(self):
        """校验端到端样例集完整性"""
        if self.verbose:
            print("\n=== 校验端到端样例集 ===")

        if "end_to_end" not in self.data:
            self.result.add_issue(
                "P0", "end_to_end_samples_missing",
                "端到端样例集文件不存在",
                ["end_to_end_samples.json"],
                "创建 end_to_end_samples.json 文件"
            )
            return

        e2e_data = self.data["end_to_end"]

        # 校验 scenarios
        if "end_to_end_scenarios" not in e2e_data:
            self.result.add_issue(
                "P0", "end_to_end_scenarios_missing",
                "端到端样例集缺少 end_to_end_scenarios 字段",
                ["end_to_end_samples.json"],
                "添加 end_to_end_scenarios 字段"
            )
            return

        scenarios = e2e_data["end_to_end_scenarios"]
        if not isinstance(scenarios, list) or len(scenarios) == 0:
            self.result.add_issue(
                "P1", "end_to_end_scenarios_empty",
                "端到端样例集应包含至少一个场景",
                ["end_to_end_scenarios"],
                "添加至少一个端到端测试场景"
            )

        # 校验每个场景的必要字段
        for i, scenario in enumerate(scenarios):
            if "scenario_id" not in scenario:
                self.result.add_issue(
                    "P1", "scenario_id_missing",
                    f"场景 {i+1} 缺少 scenario_id 字段",
                    [f"end_to_end_scenarios[{i}]"],
                    "添加 scenario_id 字段"
                )
            if "input" not in scenario:
                self.result.add_issue(
                    "P1", "scenario_input_missing",
                    f"场景 {scenario.get('scenario_id', i+1)} 缺少 input 字段",
                    [f"end_to_end_scenarios[{i}]"],
                    "添加 input 字段"
                )
            if "expected_output" not in scenario:
                self.result.add_issue(
                    "P1", "scenario_expected_output_missing",
                    f"场景 {scenario.get('scenario_id', i+1)} 缺少 expected_output 字段",
                    [f"end_to_end_scenarios[{i}]"],
                    "添加 expected_output 字段"
                )

        if self.verbose:
            print(f"[OK] 端到端样例集校验完成（共 {len(scenarios)} 个场景）")

    def validate_closure(self):
        """执行闭环校验"""
        if self.verbose:
            print("\n" + "=" * 50)
            print("AEdu KB 闭环校验")
            print("=" * 50)

        # 加载数据
        if not self.load_data():
            if self.verbose:
                print("[FAIL] 数据加载失败，无法继续校验")
            return False

        # 执行各项校验
        self.validate_frozen_values()
        self.validate_schema_compliance()
        self.validate_chapter_tree()
        self.validate_knowledge_references()
        self.validate_anchor_references()
        self.validate_dependency_graph()
        self.validate_audit_fields()
        self.validate_end_to_end_samples()

        # 生成摘要
        self.result.summary = {
            "chapter_tree_nodes": len(self.data.get("chapter_tree", {}).get("chapter_tree", [])),
            "knowledge_points": len(self.data.get("knowledge", {}).get("knowledge_points", [])),
            "ability_points": len(self.data.get("ability", {}).get("ability_points", [])),
            "anchor_points": len(self.data.get("anchor", {}).get("anchor_points", [])),
            "dependencies": len(self.data.get("dependency", {}).get("dependencies", [])),
        }

        # 输出报告
        self._print_report()

        return self.result.passed

    def _print_report(self):
        """打印校验报告"""
        report = self.result.to_report()

        print("\n" + "=" * 50)
        print("校验报告")
        print("=" * 50)
        print(f"校验 ID: {report['validation_id']}")
        print(f"校验时间：{report['validated_at']}")
        print(f"校验结果：{'PASS' if report['result'] == 'pass' else 'FAIL'}")
        print()
        print("数据摘要:")
        for key, value in report['summary'].items():
            print(f"  - {key}: {value}")
        print()
        print("问题统计:")
        print(f"  - P0 (阻断项): {report['issues']['p0_count']}")
        print(f"  - P1 (高优先级): {report['issues']['p1_count']}")
        print(f"  - P2 (次要项): {report['issues']['p2_count']}")

        if report['issues']['p0_issues']:
            print("\nP0 阻断项 (必须修复):")
            for issue in report['issues']['p0_issues']:
                print(f"  [{issue['issue_id']}] {issue['type']}: {issue['description']}")

        if report['issues']['p1_issues']:
            print("\nP1 高优先级项 (需修复):")
            for issue in report['issues']['p1_issues']:
                print(f"  [{issue['issue_id']}] {issue['type']}: {issue['description']}")

        if report['issues']['p2_issues']:
            print("\nP2 次要项 (可后续完善):")
            for issue in report['issues']['p2_issues']:
                print(f"  [{issue['issue_id']}] {issue['type']}: {issue['description']}")

        print("\n" + "=" * 50)

        # 保存报告
        report_path = self.data_dir / "validation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"报告已保存至：{report_path}")


# ============== 主函数 ==============
def main():
    parser = argparse.ArgumentParser(
        description="AEdu KB 闭环校验脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python validate_kb_closure.py --data-dir ./samples
  python validate_kb_closure.py --data-dir ./samples --verbose
        """
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="./samples",
        help="样例数据目录 (默认：./samples)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出详细日志"
    )

    args = parser.parse_args()

    validator = KBClosureValidator(args.data_dir, args.verbose)
    success = validator.validate_closure()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
