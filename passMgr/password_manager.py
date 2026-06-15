import sys
from pathlib import Path

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QApplication,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    QT6 = True
except ImportError:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import (
        QApplication,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    QT6 = False

from lightsql_store import LightSqlStore, PasswordRecord


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "passwords.db"


def set_password_mode(widget: QLineEdit, hidden: bool):
    if QT6:
        mode = QLineEdit.EchoMode.Password if hidden else QLineEdit.EchoMode.Normal
    else:
        mode = QLineEdit.Password if hidden else QLineEdit.Normal
    widget.setEchoMode(mode)


def align_center():
    return Qt.AlignmentFlag.AlignCenter if QT6 else Qt.AlignCenter


def user_role():
    return Qt.ItemDataRole.UserRole if QT6 else Qt.UserRole


class PasswordManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = LightSqlStore(DB_PATH)
        self.current_record_id: int | None = None
        self.password_hidden = True

        self.setWindowTitle("密码管理工具 - Pass Manager")
        self.resize(1120, 720)
        self.setMinimumSize(980, 620)

        self.platform_input = QLineEdit()
        self.account_input = QLineEdit()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.remark_input = QTextEdit()
        self.search_input = QLineEdit()
        self.status_label = QLabel()
        self.selected_label = QLabel("当前未选择记录")
        self.table = QTableWidget(0, 8)

        self.build_ui()
        self.apply_style()
        self.load_records()

    def build_ui(self):
        root = QWidget()
        layout = QGridLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(14)

        title = QLabel("密码管理工具")
        title.setObjectName("Title")
        subtitle = QLabel("使用 PyQt 图形界面和本地轻量 SQL 数据库存储记录")
        subtitle.setObjectName("Subtitle")

        title_box = QVBoxLayout()
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box, 0, 0, 1, 2)

        form_group = self.build_form_group()
        table_group = self.build_table_group()

        layout.addWidget(form_group, 1, 0)
        layout.addWidget(table_group, 1, 1)
        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 5)
        layout.setRowStretch(1, 1)

        self.status_label.setObjectName("Status")
        layout.addWidget(self.status_label, 2, 0, 1, 2)

        self.setCentralWidget(root)

    def build_form_group(self):
        group = QGroupBox("记录信息")
        layout = QVBoxLayout(group)

        form = QFormLayout()
        form.setLabelAlignment(align_center())

        self.platform_input.setPlaceholderText("例如：GitHub、微信、邮箱服务")
        self.account_input.setPlaceholderText("登录账号，例如账号 ID 或登录名")
        self.username_input.setPlaceholderText("用户名或昵称，可选")
        self.password_input.setPlaceholderText("登录密码")
        set_password_mode(self.password_input, True)
        self.phone_input.setPlaceholderText("绑定手机号，可选")
        self.email_input.setPlaceholderText("绑定邮箱，可选")
        self.remark_input.setPlaceholderText("备注信息，例如安全问题、用途、恢复方式")
        self.remark_input.setFixedHeight(96)

        password_row = QHBoxLayout()
        password_row.addWidget(self.password_input)
        self.toggle_password_button = QPushButton("显示")
        self.toggle_password_button.clicked.connect(self.toggle_password_visibility)
        password_row.addWidget(self.toggle_password_button)

        form.addRow("平台", self.platform_input)
        form.addRow("账号", self.account_input)
        form.addRow("用户名", self.username_input)
        form.addRow("密码", password_row)
        form.addRow("手机号", self.phone_input)
        form.addRow("邮箱", self.email_input)
        form.addRow("备注", self.remark_input)
        layout.addLayout(form)

        self.selected_label.setObjectName("Selected")
        layout.addWidget(self.selected_label)

        button_grid = QGridLayout()
        add_button = QPushButton("新增记录")
        update_button = QPushButton("修改选中")
        clear_button = QPushButton("清空表单")
        delete_button = QPushButton("删除选中")

        add_button.setObjectName("PrimaryButton")
        update_button.setObjectName("PrimaryButton")
        delete_button.setObjectName("DangerButton")

        add_button.clicked.connect(self.add_record)
        update_button.clicked.connect(self.update_record)
        clear_button.clicked.connect(self.clear_form)
        delete_button.clicked.connect(self.delete_record)

        button_grid.addWidget(add_button, 0, 0)
        button_grid.addWidget(update_button, 0, 1)
        button_grid.addWidget(clear_button, 1, 0)
        button_grid.addWidget(delete_button, 1, 1)
        layout.addLayout(button_grid)

        tips = QLabel("提示：从右侧表格选择一条记录后，可在左侧修改并保存。")
        tips.setObjectName("Tips")
        tips.setWordWrap(True)
        layout.addWidget(tips)
        layout.addStretch(1)
        return group

    def build_table_group(self):
        group = QGroupBox("查询与记录列表")
        layout = QVBoxLayout(group)

        search_row = QHBoxLayout()
        self.search_input.setPlaceholderText("输入平台、账号、用户名、手机号、邮箱或备注关键词")
        search_button = QPushButton("查询")
        reset_button = QPushButton("显示全部")
        search_button.clicked.connect(self.load_records)
        reset_button.clicked.connect(self.reset_search)
        self.search_input.returnPressed.connect(self.load_records)
        search_row.addWidget(self.search_input)
        search_row.addWidget(search_button)
        search_row.addWidget(reset_button)
        layout.addLayout(search_row)

        self.table.setHorizontalHeaderLabels(["ID", "平台", "账号", "用户名", "密码", "手机号", "邮箱", "更新时间"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows if QT6 else QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers if QT6 else QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch if QT6 else QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents if QT6 else QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.on_table_selection)
        layout.addWidget(self.table)
        return group

    def apply_style(self):
        self.setStyleSheet(
            """
            QWidget {
                color: #24313D;
                font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
                font-size: 14px;
            }
            QMainWindow, QWidget {
                background: #EEF5F1;
            }
            #Title {
                color: #1F4D3A;
                font-size: 30px;
                font-weight: 800;
            }
            #Subtitle {
                color: #667085;
                font-size: 13px;
            }
            QGroupBox {
                background: #FFFFFF;
                border: 1px solid #D7E5DD;
                border-radius: 18px;
                font-weight: 800;
                margin-top: 12px;
                padding: 18px 14px 14px 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                color: #1F4D3A;
            }
            QLineEdit, QTextEdit {
                background: #F8FBF9;
                border: 1px solid #CFE0D7;
                border-radius: 10px;
                padding: 9px;
                selection-background-color: #8CC9A7;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #4E9F6D;
                background: #FFFFFF;
            }
            QPushButton {
                background: #E5F1EA;
                border: 1px solid #C9DED2;
                border-radius: 10px;
                padding: 9px 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #D7EBDF;
            }
            #PrimaryButton {
                color: #FFFFFF;
                background: #2F8F5B;
                border-color: #2F8F5B;
            }
            #PrimaryButton:hover {
                background: #26784D;
            }
            #DangerButton {
                color: #FFFFFF;
                background: #C2410C;
                border-color: #C2410C;
            }
            #DangerButton:hover {
                background: #9A3412;
            }
            QTableWidget {
                background: #FFFFFF;
                alternate-background-color: #F6FAF7;
                border: 1px solid #D7E5DD;
                border-radius: 12px;
                gridline-color: #E7EFEA;
            }
            QHeaderView::section {
                background: #DDEEE4;
                color: #1F4D3A;
                border: 0;
                border-right: 1px solid #C9DED2;
                padding: 8px;
                font-weight: 800;
            }
            #Status {
                color: #8A4B00;
                background: #FFF7E6;
                border: 1px solid #F4D9A6;
                border-radius: 12px;
                padding: 10px 12px;
            }
            #Selected, #Tips {
                color: #667085;
                background: transparent;
                padding: 6px 2px;
            }
            """
        )

    def read_form(self):
        return {
            "platform": self.platform_input.text().strip(),
            "account": self.account_input.text().strip(),
            "username": self.username_input.text().strip(),
            "password": self.password_input.text(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "remark": self.remark_input.toPlainText().strip(),
        }

    def validate_form(self, data):
        missing = []
        if not data["platform"]:
            missing.append("平台")
        if not data["account"]:
            missing.append("账号")
        if not data["password"]:
            missing.append("密码")

        if missing:
            self.show_warning(f"请填写必填字段：{'、'.join(missing)}。")
            return False
        return True

    def add_record(self):
        data = self.read_form()
        if not self.validate_form(data):
            return

        record_id = self.store.add_record(**data)
        self.current_record_id = record_id
        self.set_status(f"已新增记录：{data['platform']} / {data['account']}。")
        self.load_records()
        self.select_record_in_table(record_id)

    def update_record(self):
        if self.current_record_id is None:
            self.show_warning("请先在右侧表格选择一条要修改的记录。")
            return

        data = self.read_form()
        if not self.validate_form(data):
            return

        updated = self.store.update_record(self.current_record_id, **data)
        if updated:
            self.set_status(f"已修改记录：{data['platform']} / {data['account']}。")
            self.load_records()
            self.select_record_in_table(self.current_record_id)
        else:
            self.show_warning("未找到要修改的记录，请刷新后再试。")

    def delete_record(self):
        if self.current_record_id is None:
            self.show_warning("请先选择一条要删除的记录。")
            return

        should_delete = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除当前选中的密码记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No if QT6 else QMessageBox.Yes | QMessageBox.No,
        )
        yes_value = QMessageBox.StandardButton.Yes if QT6 else QMessageBox.Yes
        if should_delete != yes_value:
            return

        deleted = self.store.delete_record(self.current_record_id)
        if deleted:
            self.set_status("已删除选中的记录。")
            self.clear_form()
            self.load_records()
        else:
            self.show_warning("删除失败，记录可能已经不存在。")

    def load_records(self):
        keyword = self.search_input.text().strip()
        records = self.store.search_records(keyword)
        self.fill_table(records)
        if keyword:
            self.set_status(f"查询完成：找到 {len(records)} 条匹配记录。")
        else:
            self.set_status(f"当前共有 {len(records)} 条密码记录。")

    def fill_table(self, records: list[PasswordRecord]):
        self.table.setRowCount(0)
        for row_index, record in enumerate(records):
            self.table.insertRow(row_index)
            values = [
                str(record.record_id),
                record.platform,
                record.account,
                record.username,
                self.mask_password(record.password),
                record.phone,
                record.email,
                record.updated_at,
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(user_role(), record)
                if col_index == 0:
                    item.setTextAlignment(align_center())
                self.table.setItem(row_index, col_index, item)

    def on_table_selection(self):
        selected = self.table.selectedItems()
        if not selected:
            return

        record = selected[0].data(user_role())
        if not isinstance(record, PasswordRecord):
            return

        self.current_record_id = record.record_id
        self.platform_input.setText(record.platform)
        self.account_input.setText(record.account)
        self.username_input.setText(record.username)
        self.password_input.setText(record.password)
        self.phone_input.setText(record.phone)
        self.email_input.setText(record.email)
        self.remark_input.setPlainText(record.remark)
        display_name = record.username or record.account
        self.selected_label.setText(f"当前选中：#{record.record_id} {record.platform} / {display_name}")

    def select_record_in_table(self, record_id):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == str(record_id):
                self.table.selectRow(row)
                return

    def reset_search(self):
        self.search_input.clear()
        self.load_records()

    def clear_form(self):
        self.current_record_id = None
        self.platform_input.clear()
        self.account_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.phone_input.clear()
        self.email_input.clear()
        self.remark_input.clear()
        self.selected_label.setText("当前未选择记录")
        self.table.clearSelection()
        self.set_status("表单已清空，可以新增记录。")

    def toggle_password_visibility(self):
        self.password_hidden = not self.password_hidden
        set_password_mode(self.password_input, self.password_hidden)
        self.toggle_password_button.setText("显示" if self.password_hidden else "隐藏")

    def set_status(self, text):
        self.status_label.setText(text)

    def show_warning(self, text):
        QMessageBox.warning(self, "提示", text)
        self.set_status(text)

    @staticmethod
    def mask_password(password):
        if not password:
            return ""
        return "•" * min(12, max(6, len(password)))


def main():
    app = QApplication(sys.argv)
    window = PasswordManagerWindow()
    window.show()
    sys.exit(app.exec() if QT6 else app.exec_())


if __name__ == "__main__":
    main()
