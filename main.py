from contextlib import nullcontext
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
from dbservice import DBService
from command import Command
import SingletonGuardWin as sgw
from datetime import datetime as dt
import os
import sys
import threading
import psutil
import pystray
from PIL import Image


class TreeviewRowExtra:
    def __init__(self, id: str, row_id: str) -> None:
        self.id = id
        self.row_id = row_id
        self.is_modified = False


class CmdManager:

    unchecked_symbol = "□"
    checked_symbol = "■"
    checked_bg_color = "#0078d7"
    checked_fore_color = "#ffffff"
    unchecked_bg_color = checked_fore_color
    unchecked_fore_color = "#000000"
    # 定义字体
    normal_font = ("微软雅黑", 10)
    big_font = ("微软雅黑", 12)
    entry_placeholders = dict()
    treeviewRowExtras = dict[str, TreeviewRowExtra]()

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Windows命令行管理器")

        screenwidth = root.winfo_screenwidth()  # 屏幕宽度
        screenheight = root.winfo_screenheight()  # 屏幕高度
        width = 1000
        height = 500
        x = int((screenwidth - width) / 2)
        y = int((screenheight - height) / 2)
        root.geometry(f"{width}x{height}+{x}+{y}")  # 大小以及位置

        self.root.protocol("WM_DELETE_WINDOW", self.on_minimize)
        # 这会同时影响窗口标题栏和任务栏图标
        self.root.iconbitmap(resource_path("app.ico"))

        # 创建系统托盘图标
        self.create_tray_icon()

        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        # 配置网格布局
        self.main_frame.rowconfigure(3, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        # 输入区域
        input_frame = ttk.LabelFrame(self.main_frame, text="命令输入", padding=5)
        input_frame.grid(row=0, column=0, sticky=tk.NSEW, pady=5)

        # 增加两行间距
        input_frame.rowconfigure(1, minsize=40)
        for i in range(2):
            input_frame.rowconfigure(i, weight=1)
            # 设置5列（取两行中最大列数）的权重
        for i in range(5):
            # uniform参数确保列宽相同
            input_frame.columnconfigure(i, weight=1, uniform="cols")
        # input_frame.columnconfigure([0, 1, 2, 3], weight=1)  # 使整个框架可以水平扩展

        # 名称字段
        self.name_placeholder = "请输入名称"
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(input_frame, textvariable=self.name_var)
        self.name_entry.insert(0, self.name_placeholder)
        self.name_entry.config(foreground="grey")
        self.name_entry.bind(
            "<FocusIn>", lambda e: self.on_entry_focus_in(e, self.name_placeholder)
        )
        self.name_entry.bind(
            "<FocusOut>", lambda e: self.on_entry_focus_out(e, self.name_placeholder)
        )
        self.name_entry.grid(row=0, column=0, sticky=tk.EW, padx=5)
        self.name_var.trace_add("write", lambda *args: self.update_button_states())
        self.entry_placeholders[self.name_entry] = self.name_placeholder

        # 命令字段
        self.cmd_placeholder = "请输入命令或选择文件"
        self.cmd_var = tk.StringVar()
        self.cmd_entry = ttk.Entry(input_frame, textvariable=self.cmd_var)
        self.cmd_entry.insert(0, self.cmd_placeholder)
        self.cmd_entry.config(foreground="grey")
        self.cmd_entry.bind(
            "<FocusIn>", lambda e: self.on_entry_focus_in(e, self.cmd_placeholder)
        )
        self.cmd_entry.bind(
            "<FocusOut>", lambda e: self.on_entry_focus_out(e, self.cmd_placeholder)
        )
        self.cmd_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.cmd_var.trace_add("write", lambda *args: self.update_button_states())
        self.entry_placeholders[self.cmd_entry] = self.cmd_placeholder

        # 在初始化部分添加文件选择按钮
        self.cmd_button = ttk.Button(
            input_frame,
            text="选择文件",
            command=self.select_cmd_file,
            style="Accent.TButton",
        )
        self.cmd_button.grid(row=0, column=2, sticky=tk.EW, padx=5)

        # 备注字段
        self.remark_placeholder = "请输入备注信息"
        self.remark_var = tk.StringVar()
        self.remark_entry = ttk.Entry(input_frame, textvariable=self.remark_var)
        self.remark_entry.insert(0, self.remark_placeholder)
        self.remark_entry.config(foreground="grey")
        self.remark_entry.bind(
            "<FocusIn>", lambda e: self.on_entry_focus_in(e, self.remark_placeholder)
        )
        self.remark_entry.bind(
            "<FocusOut>", lambda e: self.on_entry_focus_out(e, self.remark_placeholder)
        )
        self.remark_entry.grid(row=0, column=3, sticky=tk.EW, padx=5)
        self.remark_var.trace_add("write", lambda *args: self.update_button_states())
        self.entry_placeholders[self.remark_entry] = self.remark_placeholder

        # 隐藏的id字段
        self.id_var = tk.StringVar()
        self.id_var.trace_add("write", lambda *args: self.update_button_states())

        self.save_button = ttk.Button(
            input_frame, text="保存", state=tk.DISABLED, command=self.save_command
        )
        self.save_button.grid(row=1, column=0, sticky=tk.EW, padx=5)

        self.delete_button = ttk.Button(
            input_frame,
            text="删除",
            state=tk.DISABLED,
            command=self.delete_commands,
        )
        self.delete_button.grid(row=1, column=1, sticky=tk.EW, padx=5)

        self.run_button = ttk.Button(
            input_frame, text="执行", state=tk.DISABLED, command=self.run_command
        )
        self.run_button.grid(row=1, column=2, sticky=tk.EW, padx=5)

        self.deselect_button = ttk.Button(
            input_frame,
            text="取消选择",
            state=tk.DISABLED,
            command=self.clear_selection,
        )
        self.deselect_button.grid(row=1, column=3, sticky=tk.EW, padx=5)

        self.clear_inputs_button = ttk.Button(
            input_frame, text="清空", command=self.clear_inputs
        )
        self.clear_inputs_button.grid(row=1, column=4, sticky=tk.EW, padx=5)

        # 命令列表容器
        self.cmd_list_frame = ttk.LabelFrame(self.main_frame, text="命令列表")
        self.cmd_list_frame.grid(
            row=2, column=0, sticky=tk.NSEW, padx=5, pady=5, columnspan=2
        )

        # 列表容器
        self.cmd_list_container = tk.Frame(self.cmd_list_frame)
        self.cmd_list_container.pack(fill=tk.BOTH, expand=True)

        # 滚动条
        tree_scrollbar = tk.Scrollbar(self.cmd_list_container)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 命令列表
        self.cmd_tree = ttk.Treeview(
            self.cmd_list_container,
            columns=("id", "name", "command", "remark", "selected"),
            displaycolumns=("selected", "name", "command", "remark"),
            show="headings",
            yscrollcommand=tree_scrollbar.set,
            # selectmode="extended", # 多选模式
        )
        self.cmd_tree.tag_configure(
            "selected",
            background=self.checked_bg_color,
            foreground=self.checked_fore_color,
        )
        # 应用字体样式
        style = ttk.Style()
        style.configure(
            "Treeview", background=self.unchecked_bg_color, font=self.normal_font
        )
        style.configure("Treeview.Heading", font=self.big_font)
        style.configure(
            "Treeview.selected", background=self.checked_bg_color, font=self.big_font
        )

        style.map(
            "Treeview",
            background=[("selected", self.checked_bg_color)],
            font=[("selected", self.big_font)],
        )

        tree_scrollbar.config(command=self.cmd_tree.yview)

        self.cmd_tree.heading("selected", text="选择")
        self.cmd_tree.heading("name", text="名称")
        self.cmd_tree.heading("command", text="命令")
        self.cmd_tree.heading("remark", text="备注")
        # 设置列宽可调整
        self.cmd_tree.column("selected", width=50, stretch=False)
        self.cmd_tree.column("name", width=100, stretch=True)
        self.cmd_tree.column("command", width=200, stretch=True)
        self.cmd_tree.column("remark", width=100, stretch=True)

        self.cmd_tree.pack(fill="both", expand=True)
        self.cmd_tree.bind("<Button-1>", self.on_treeview_click)
        self.cmd_tree.bind("<Double-1>", self.on_treeview_double_click)

        # 输出区域
        output_frame = ttk.Frame(self.main_frame)
        output_frame.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)

        # 添加垂直滚动条
        output_scrollbar = ttk.Scrollbar(output_frame)
        output_scrollbar.pack(side="right", fill="y")

        self.output_text = tk.Text(
            output_frame, height=0, yscrollcommand=output_scrollbar.set
        )
        self.output_text.pack(side="left", fill=tk.BOTH, expand=True)
        self.output_text.tag_config("error", foreground="red")
        output_scrollbar.config(command=self.output_text.yview)

        # 初始化数据库
        self.init_db()
        # 加载已存储命令
        self.load_commands()

    # 弃用
    def set_widget_ui(self):
        def get_all_children(widget):
            children = widget.winfo_children()
            for child in children:
                yield child
                yield from get_all_children(child)

        # 在窗口初始化部分添加样式设置
        style = ttk.Style()

        # 设置ttk.Button样式
        style.configure(
            "TButton",
            background="#7FFFD4",  # 浅绿色
            font=self.normal_font,
        )
        style.map("TButton", background=[("active", "#90ee90")])  # 激活状态颜色

        # 设置ttk.Frame样式
        style.configure(
            "TFrame",
            background="#e6e6fa",  # 薰衣草色
        )

        all_widgets = list(get_all_children(self.root))
        # 应用样式到现有组件
        for widget in all_widgets:
            if isinstance(widget, ttk.Button):
                widget.configure(style="TButton")
            elif isinstance(widget, ttk.Frame | ttk.LabelFrame):
                widget.configure(style="TFrame")
            # elif isinstance(widget, ttk.LabelFrame):
            #     widget.configure(style="TFrame")

    def create_tray_icon(self):
        ico = Image.open(resource_path("app.ico"))
        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", self.show_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self.quit_app),
        )

        self.tray_icon = pystray.Icon("CmdManager", ico, menu=menu)

        # 在新线程中运行托盘图标
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

    def show_window(self, icon):
        def _show():
            self.root.deiconify()
            self.root.lift()

        self.root.after(0, lambda: _show())

    def quit_app(self, icon):
        # 使用线程安全方式停止托盘图标
        def stop_tray():
            if not hasattr(self, "tray_icon") or not self.tray_icon:
                return

            self.tray_icon.stop()
            self.root.quit()
            self.root.destroy()

        # 在主线程执行销毁操作
        self.root.after(0, lambda: stop_tray())

    def on_minimize(self):
        self.root.withdraw()

    # 添加文件选择方法
    def select_cmd_file(self):
        file_path = filedialog.askopenfilename(
            title="选择命令文件",
            filetypes=[("CMD文件", "*.cmd"), ("BAT文件", "*.bat"), ("所有文件", "*.*")],
        )
        if not file_path:
            return

        self.cmd_var.set(file_path)
        # 手动触发按钮状态更新
        self.update_button_states()

    def init_db(self):
        try:
            self.db_service = DBService()
        except Exception as e:
            messagebox.showerror("初始化错误", f"无法初始化数据库: {str(e)}")

    def load_commands(self):
        try:
            commands = self.db_service.get_commands()
            self.cmd_tree.delete(*self.cmd_tree.get_children())
            if not commands:
                vals = ("", "没有存储的命令", "", "", self.unchecked_symbol)
                self.cmd_tree.insert("", tk.END, values=vals)
                return
            # print(f"加载的命令: {commands}")  # 调试信息
            for cmd in commands:
                vals = (
                    cmd.id,
                    cmd.name,
                    cmd.command,
                    cmd.notes or "",
                    self.unchecked_symbol,
                )
                row_id = self.cmd_tree.insert("", tk.END, values=vals)
                self.treeviewRowExtras[cmd.id] = TreeviewRowExtra(cmd.id, row_id)

        except Exception as e:
            messagebox.showerror("加载错误", f"无法加载命令: {str(e)}")
            # 调试信息
            print(f"加载命令时出错: {e}")

    def edit_command(self, item):
        """编辑命令"""
        try:
            item_values = self.cmd_tree.item(item, "values")
            print(f"原始值: {item_values}")  # 调试信息

            item_id = item_values[0] if len(item_values) > 0 else ""
            self.id_var.set(item_id)

            self.name_entry.delete(0, tk.END)
            self.cmd_entry.delete(0, tk.END)
            self.remark_entry.delete(0, tk.END)

            if len(item_values) >= 3:
                self.name_entry.insert(0, item_values[1])
                self.cmd_entry.insert(0, item_values[2])
                self.remark_entry.insert(0, item_values[3])
        except Exception as e:
            messagebox.showerror("错误", f"编辑命令失败: {str(e)}")

    def save_command(self):
        """保存当前命令"""
        try:
            name = self.name_entry.get().strip(self.name_placeholder)
            command = self.cmd_entry.get().strip(self.cmd_placeholder)
            remark = self.remark_entry.get().strip(self.remark_placeholder)
            # TODO
            if not name or not command:
                messagebox.showwarning("警告", "名称和命令不能为空")
                return

            modified_items = [
                (v.row_id, v.id)
                for _, v in self.treeviewRowExtras.values()
                if v.is_modified
            ]
            all_values = [
                self.cmd_tree.item(row_id, "values") for row_id, _ in modified_items
            ]
            # TODO
            itemid = self.id_var.get()
            if itemid:  # 更新已有命令
                self.db_service.update_command(Command(name, command, remark, itemid))
            else:  # 新增命令
                self.db_service.save_command(Command(name, command, remark))

            self.load_commands()

            # 清空输入框
            self.name_entry.delete(0, tk.END)
            self.cmd_entry.delete(0, tk.END)
            self.remark_entry.delete(0, tk.END)
            self.id_var.set("")

        except Exception as e:
            messagebox.showerror("错误", f"保存命令失败: {str(e)}")

    def update_button_states(self):
        """根据id_var状态更新按钮可用性"""
        has_id = bool(self.id_var.get())
        cmd = self.cmd_entry.get()
        name = self.name_entry.get()
        is_input_fill = (
            name
            and cmd
            and name != self.name_placeholder
            and cmd != self.cmd_placeholder
        )
        self.save_button.config(
            state=tk.NORMAL if has_id or is_input_fill else tk.DISABLED
        )
        self.delete_button.config(state=tk.NORMAL if has_id else tk.DISABLED)
        self.deselect_button.config(state=tk.NORMAL if has_id else tk.DISABLED)

        # """根据输入框内容更新执行按钮状态"""
        can_run = cmd and cmd != self.cmd_placeholder
        self.run_button.config(state=tk.NORMAL if can_run else tk.DISABLED)

        self.update_input_config()

    def update_input_config(self):
        """根据输入框内容更新输入框配置"""
        for entry in [self.name_entry, self.cmd_entry, self.remark_entry]:
            val = entry.get()
            if val and val != self.entry_placeholders[entry]:
                entry.config(foreground="black")
            else:
                entry.config(foreground="grey")

    def clear_inputs(self):
        """清空所有输入框"""
        self.name_entry.delete(0, tk.END)
        self.cmd_entry.delete(0, tk.END)
        self.remark_entry.delete(0, tk.END)
        self.name_entry.insert(0, self.name_placeholder)
        self.cmd_entry.insert(0, self.cmd_placeholder)
        self.remark_entry.insert(0, self.remark_placeholder)

        self.id_var.set("")
        self.update_button_states()

    def clear_selection(self):
        """取消当前选择"""
        self.cmd_tree.selection_remove(self.cmd_tree.selection())
        self.clear_inputs()

    def on_entry_focus_in(self, event, placeholder):
        entry = event.widget
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(foreground="black")

    def on_entry_focus_out(self, event, placeholder):
        entry = event.widget
        if not entry.get():
            entry.insert(0, placeholder)
            entry.config(foreground="grey")

    def delete_commands(self):
        """删除选中的命令"""
        selected_items = self.cmd_tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的命令")
            return

        command_ids = [self.cmd_tree.item(item, "values")[0] for item in selected_items]
        try:
            cmfirmsg = f"确定要删除选中的{len(command_ids)}条命令吗?"
            if not messagebox.askyesno("确认", cmfirmsg):
                return

            self.db_service.delete_commands(command_ids)
            self.load_commands()

            self.clear_inputs()
        except Exception as e:
            messagebox.showerror("错误", f"删除命令失败: {str(e)}")

    def on_treeview_click(self, event):
        """处理treeview点击事件，包括checkbox和编辑"""
        item = self.cmd_tree.identify_row(event.y)
        column = self.cmd_tree.identify_column(event.x)
        # print(item, column)
        # print(f"selected:{item in self.cmd_tree.selection()}")  # 第二次点击当前行

        tags = None
        # 如果是点击了checkbox列
        if column == "#1":
            values = list(self.cmd_tree.item(item, "values"))
            val = self.checked_symbol
            # print(f"当前值: {current_value}")
            if values[4] == unchecked_symbol:
                tags = ("selected",)
            else:
                tags = ()
                val = self.unchecked_symbol
                self.cmd_tree.selection_remove(item)

            values[4] = val
            # print(f"after:{val = },{bg_color = },{fore_color = },{tags = }")
            self.cmd_tree.item(item, values=values, tags=(tags))

        # 获取cmd_tree的所有行的tags
        # all_tags = [self.cmd_tree.item(item, "tags") for item in self.cmd_tree.get_children()]
        # print(f"{all_tags = }")
        # all_values = [self.cmd_tree.item(item, "values") for item in self.cmd_tree.get_children()]
        # print(f"{all_values = }")
        self.on_cmd_edit(event)
        if tags and tags.count("selected") == 0:
            # 阻止后续默认处理
            return "break"

    def on_treeview_double_click(self, event):
        region = self.cmd_tree.identify_region(event.x, event.y)  # 判断点击区域
        if region != "cell":
            return  # 仅响应单元格双击

        column = self.cmd_tree.identify_column(event.x)  # 获取列ID（如 '#1'）
        if column == "#1":
            return

        row_id = self.cmd_tree.focus()  # 获取当前选中行ID
        print(row_id, column)
        column_index = int(column[1:]) - 1  # 列索引（0开始）

        # 获取单元格原始值
        values = self.cmd_tree.item(row_id, "values")
        old_value = values[column_index]

        # 创建临时Entry控件
        entry_edit = ttk.Entry(self.cmd_tree)
        entry_edit.insert(0, old_value)
        entry_edit.select_range(0, tk.END)  # 全选文本

        # 定位Entry到单元格位置
        x, y, width, height = self.cmd_tree.bbox(row_id, column)
        entry_edit.place(x=x, y=y, width=width, height=height)

        # 绑定保存和取消事件
        entry_edit.bind(
            "<Return>",
            lambda e: self.save_tree_view_edit(row_id, column_index, entry_edit),
        )
        entry_edit.bind(
            "<FocusOut>",
            lambda e: self.save_tree_view_edit(row_id, column_index, entry_edit),
        )
        entry_edit.bind("<Escape>", lambda e: entry_edit.destroy())
        entry_edit.focus_set()

    def save_tree_view_edit(self, row_id, column_index, entry):
        """保存编辑后的内容到Treeview"""
        new_value = entry.get()
        # TODO check the new_value is the same as old_value
        values = list(self.cmd_tree.item(row_id, "values"))  # 转为可变列表
        values[column_index] = new_value
        self.cmd_tree.item(row_id, values=values)  # 更新数据
        # TODO update treeviewRowExtra dict
        entry.destroy()  # 销毁临时Entry

    def on_cmd_edit(self, event):
        """双击编辑命令"""
        item = self.cmd_tree.identify_row(event.y)
        if item:
            self.edit_command(item)

    def run_command(self):
        selected_items = self.cmd_tree.selection() or []

        commands = []
        for item in selected_items:
            values = self.cmd_tree.item(item, "values")
            if len(values) > 2 and values[2] is not None:  # 假设命令在第二列
                commands.append(values[2])

        cur_cmd = self.cmd_entry.get()
        if cur_cmd and cur_cmd not in commands:
            commands.append(cur_cmd)

        if not commands or len(commands) == 0:
            messagebox.showwarning("警告", "请先[选择/填入]要执行的命令")
            return

        for command in commands:
            self.run(command)

    def run(self, command: str):
        """执行命令"""
        try:
            isFile = os.path.isfile(command)
            stdout, stderr = None, None
            output_type = subprocess.DEVNULL if isFile else subprocess.PIPE
            # 如果是文件，直接执行不等待输出
            subpro = subprocess.Popen(
                command,
                shell=True,
                stdout=output_type,
                stderr=output_type,
            )
            if isFile:
                stdout = "已执行文件"
            else:
                stdout, stderr = subpro.communicate()

            self.output_text.see(tk.END)  # 自动滚动到最后
            self.output_text.update()
            # print(f"{stdout = }")  # 调试信息
            # print(f"{stderr = }")  # 调试信息

            self.output_text.insert(tk.END, f'\n{"-" * 50}\n', "separator")
            self.output_text.insert(
                tk.END, dt.now().strftime("%y-%m-%d %H:%M:%S") + ":[" + command + "]\n"
            )

            # 根据是否有错误决定是否展开输出区域
            if stderr:
                self.output_text.insert(tk.END, stderr, "error")
            elif stdout:
                self.output_text.insert(tk.END, stdout)
            else:
                self.output_text.append_output("执行成功")

        except Exception as e:
            self.output_text.insert(tk.END, f"错误: {str(e)}", "error")


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def check_single_instance(lock_file_path):
    if os.name == "nt":
        return sgw.SingletonGuardWin(lock_file_path)

    return nullcontext()

    # pyinstaller 打包会开启一个守护进程，导致ppid是守护进程的pid
    current_pid = os.getpid()
    current_ppid = os.getppid()
    current_name = (
        psutil.Process().name()
    )  # os.path.basename(sys.argv[0])  # 获取当前脚本名
    pros = list(psutil.process_iter(["name", "exe"]))
    same_names = [
        (proc.pid, proc.ppid()) for proc in pros if proc.info["name"] == current_name
    ]
    messagebox.showinfo(
        "当前进程信息",
        f"{current_pid}:{current_name},{current_pid = },{current_ppid = },{len(pros) = },{same_names = }",
    )

    for proc in pros:
        try:
            # 精确匹配：进程名相同且非当前进程
            if (
                proc.info["name"] == current_name
                and proc.pid != current_pid
                and proc.ppid() != current_ppid
            ):
                messagebox.showerror(
                    "程序已在运行中", f"进程ID: {proc.pid},{proc.name}"
                )
                sys.exit(1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


if __name__ == "__main__":
    with check_single_instance("CmdManager.lock"):
        root = tk.Tk()
        app = CmdManager(root)
        root.mainloop()
