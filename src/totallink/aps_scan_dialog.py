"""
APS 扫描结果展示对话框

接收 linkDMDatasetResult 返回的表头(TMESEXC15)和表身(TMESEXC16)数据，
以结构化界面展示批次信息和配方明细。
"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# ── 表头字段映射 ──────────────────────────────────────────────
HEADER_FIELDS: list[tuple[str, str]] = [
    ("APSNUM", "APS 编号"),
    ("MFGNUM", "制造批号"),
    ("DOCDAT", "单据日期"),
    ("ITMNAM", "品名"),
    ("ITMNO", "品号"),
    ("HQTYSTU", "计划数量"),
    ("LQTYSTU", "损耗量"),
    ("STU", "单位"),
    ("DEVSEQ", "设备编号"),
    ("OPESPL", "操作员"),
    ("REMARK", "备注"),
]

# ── 表身表格列定义 ────────────────────────────────────────────
BODY_COLUMNS: list[tuple[str, str]] = [
    ("CPNITMNO", "物料编号"),
    ("ITMNAM", "物料名称"),
    ("MATRAT", "配比 (%)"),
    ("CPNQTYSTU", "数量"),
    ("CPNSTU", "单位"),
]

# 需要格式化的日期字段（key → 截取长度）
DATE_KEYS = frozenset({"DOCDAT"})
DATE_FMT_LEN = 10  # "2026-06-08"


def _fmt_cell(value: Any) -> str:
    """安全地将单元格值转为展示字符串。"""
    if value is None:
        return ""
    return str(value)


def _fmt_date(raw: str) -> str:
    """截取日期时间字符串的前 10 位 (yyyy-MM-dd)。"""
    if not raw:
        return ""
    return raw[:DATE_FMT_LEN]


class ApsScanDialog(QDialog):
    """APS 扫描结果展示对话框。"""

    def __init__(
            self,
            head: dict[str, Any] | None = None,
            body: dict[str, Any] | None = None,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("APS 扫描结果")
        self.setMinimumSize(800, 560)
        self.resize(860, 620)

        self._head: dict[str, Any] = head or {}
        self._body: dict[str, Any] = body or {}

        self._setup_ui()
        self._populate()

    # ── UI 构建 ────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 20, 24, 20)

        # 顶部标题
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label = QLabel("APS 批次详情")
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title_label)

        # ── 表头 ──
        root.addWidget(self._build_header_group())

        # ── 表身 ──
        root.addWidget(self._build_body_group(), stretch=1)

        # ── 底部按钮 ──
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

    def _build_header_group(self) -> QGroupBox:
        group = QGroupBox("批次信息（表头）")
        layout = QFormLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 20, 16, 16)

        self._header_widgets: dict[str, QLineEdit] = {}
        for key, label_text in HEADER_FIELDS:
            edit = QLineEdit()
            edit.setReadOnly(True)
            edit.setMinimumHeight(32)
            edit.setMinimumWidth(240)
            edit.setStyleSheet(self._readonly_style())
            self._header_widgets[key] = edit
            layout.addRow(f"{label_text}:", edit)

        # 两列布局提示：FormLayout 默认足够紧凑；如需更紧凑可改用 GridLayout
        return group

    def _build_body_group(self) -> QGroupBox:
        group = QGroupBox("配方明细（表身）")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 20, 16, 16)

        self._body_table = QTableWidget()
        self._body_table.setColumnCount(len(BODY_COLUMNS))
        self._body_table.setHorizontalHeaderLabels(
            [label for _, label in BODY_COLUMNS]
        )
        self._body_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._body_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._body_table.setAlternatingRowColors(True)
        self._body_table.verticalHeader().setVisible(False)

        header = self._body_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._body_table)
        return group

    # ── 数据填充 ───────────────────────────────────────────────

    def _populate(self) -> None:
        self._populate_header()
        self._populate_body()

    def _populate_header(self) -> None:
        head_row = self._head.get("Table", [{}])
        first: dict[str, Any] = head_row[0] if head_row else {}

        for key, edit in self._header_widgets.items():
            raw = first.get(key)
            if key in DATE_KEYS:
                edit.setText(_fmt_date(str(raw)))
            elif key in ("HQTYSTU", "LQTYSTU") and raw is not None:
                # 数量保留最多 2 位小数
                try:
                    edit.setText(f"{float(raw):.3f}")
                except (ValueError, TypeError):
                    edit.setText(_fmt_cell(raw))
            else:
                edit.setText(_fmt_cell(raw))

    def _populate_body(self) -> None:
        rows = self._body.get("Table", [])
        self._body_table.setRowCount(len(rows))

        key_order = [key for key, _ in BODY_COLUMNS]

        for r, row_data in enumerate(rows):
            for c, key in enumerate(key_order):
                value = row_data.get(key, "")
                if key == "MATRAT" and value is not None:
                    try:
                        value = f"{float(value):.0f}%"
                    except (ValueError, TypeError):
                        value = str(value)
                elif key == "CPNQTYSTU" and value is not None:
                    try:
                        value = f"{float(value):.3f}"
                    except (ValueError, TypeError):
                        value = str(value)
                else:
                    value = _fmt_cell(value)

                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._body_table.setItem(r, c, item)

    # ── 样式 ────────────────────────────────────────────────────

    @staticmethod
    def _readonly_style() -> str:
        return (
            "QLineEdit {"
            "  background-color: #f5f5f5;"
            "  border: 1px solid #dcdcdc;"
            "  border-radius: 6px;"
            "  padding: 6px 12px;"
            "  color: #333333;"
            "  font-size: 13px;"
            "}"
        )


# ── 独立运行演示 ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication

    # ---- 模拟数据 （来自实际 API 响应） ----
    demo_head = {
        "data": {
            "Table": [
                {
                    "APSLIN": 4,
                    "APSNUM": "APS0000000295",
                    "DEVSEQ": "01-IMF60",
                    "DOCDAT": "2026-06-08T00:00:00",
                    "HQTYSTU": 1110.0,
                    "ITMNAM": "难易拼配",
                    "ITMNO": "0401NY01",
                    "LQTYSTU": 58.42,
                    "MFGNUM": "MFG260600004",
                    "OPESPL": 19,
                    "REMARK": "",
                    "STU": "KG",
                }
            ]
        },
        "isSuccess": "true",
    }

    demo_body = {
        "data": {
            "Table": [
                {
                    "CPNITMNO": "01F41",
                    "CPNQTYSTU": 0.0,
                    "CPNSTU": "KG",
                    "ITMNAM": "乌干达罗布斯塔",
                    "LOC": None,
                    "MATRAT": 60.0,
                    "MWEIQTY": None,
                    "OKFLG": None,
                    "REMARK": "",
                },
                {
                    "CPNITMNO": "01F76",
                    "CPNQTYSTU": 0.0,
                    "CPNSTU": "KG",
                    "ITMNAM": "利姆UG水洗",
                    "LOC": None,
                    "MATRAT": 40.0,
                    "MWEIQTY": None,
                    "OKFLG": None,
                    "REMARK": "",
                },
            ]
        },
        "isSuccess": "true",
    }

    app = QApplication(sys.argv)

    # 设置全局字体（适配中文）
    font = app.font()
    font.setPointSize(11)
    app.setFont(font)

    dlg = ApsScanDialog(
        head=demo_head["data"],
        body=demo_body["data"],
    )

    if dlg.exec() == QDialog.DialogCode.Accepted:
        print("用户确认 — 可在此将数据写回烘焙属性对话框")
    else:
        print("用户取消")

    sys.exit(0)
