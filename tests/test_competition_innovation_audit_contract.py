import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "competition_innovation_audit.md"


class CompetitionInnovationAuditContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = AUDIT.read_text(encoding="utf-8")

    def test_required_deliverables_are_explicit(self):
        for phrase in (
            "Application Solution Report",
            "Product Prototype and Model Design",
            "Presentation Deck",
            "Prototype Demonstration Video",
            "不超过 3 分钟",
        ):
            self.assertIn(phrase, self.text)

    def test_scientific_boundaries_are_explicit(self):
        for phrase in (
            "代理标签",
            "合成演示服务已从仓库删除",
            "当前产品不展示MCR",
            "合成训练闭环",
            "不能写成 “outperforms existing models”",
            "不证明跨年、跨区域或业务泛化",
        ):
            self.assertIn(phrase, self.text)

    def test_verified_hazard_metrics_are_not_hidden(self):
        for phrase in (
            "PR-AUC 0.795",
            "CSI 0.552",
            "POD 0.100",
            "FAR 0.803",
            "PR-AUC 0.164",
            "FAR 0.865",
        ):
            self.assertIn(phrase, self.text)

    def test_compliance_and_priority_are_covered(self):
        for phrase in (
            "数据授权清单",
            "地图合规",
            "P0：先消除提交阻断",
            "P1：把产品故事接成一条真实链",
            "P2：只做一个能增强创新证据的实验",
            "没有继续引入外部大模型不是主要短板",
        ):
            self.assertIn(phrase, self.text)


if __name__ == "__main__":
    unittest.main()
