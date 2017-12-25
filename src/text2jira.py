import argparse
import sqlite3
import tkinter as tk
import tkinter.ttk as ttk
import traceback
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showinfo, showerror

from jira import JIRA

MAX_RESULTS = 100000


def create_issues_in_jira(*, issue_dicts, server_url, basic_auth, board_name, assignee_key, components, max_results):
    jira = JIRA(server=server_url, basic_auth=basic_auth)

    def get_board(board_name):
        for board in jira.boards():
            if board.name == board_name:
                return board
        return None

    def get_project(project_name):
        for project in jira.projects():
            if project.name == project_name:
                return project
        return None

    board = get_board(board_name)
    if not board:
        raise Exception('board not found: \'{}\''.format(board_name))
    project = get_project(board.location.displayText)

    component_ids = None
    if components is not None:
        component_objs = jira.project_components(project)

        def get_component(component_name):
            for component_obj in component_objs:
                if component_obj.name == component_name:
                    return component_obj
            return None

        component_ids = []
        for component in components:
            component_obj = get_component(component)
            if component_obj is None:
                raise Exception('component not found: \'{}\''.format(component))
            component_ids.append(component_obj.id)

    create_issues_results = []

    def _create_issue(issue_dict, parent=None):
        fields_list = [
            {
                'project': {'key': project.key},
                'summary': issue_dict['summary'],
                'description': issue_dict['description'],
                'issuetype': {'name': 'Task' if parent is None else 'Sub-task'},
                'assignee': {'name': assignee_key}
            }
        ]
        if component_ids is not None:
            fields_list[0]['components'] = [{'id': component_id} for component_id in component_ids]
        if parent is not None:
            fields_list[0]['parent'] = {'key': parent.key}
        results = jira.create_issues(fields_list)
        assert len(results) == 1
        result = results[0]
        issue_obj = result['issue']
        for sub_issue_dict in issue_dict['sub_issues']:
            _create_issue(sub_issue_dict, issue_obj)
        create_issues_results.append(dict(issue_dict=issue_dict, issue_obj=issue_obj))

    for issue_dict in issue_dicts:
        _create_issue(issue_dict)

    issues_to_add_to_sprint = [create_issues_result['issue_obj'].key
                               for create_issues_result in create_issues_results
                               if create_issues_result['issue_dict'].get('add_to_sprint', False)]
    if issues_to_add_to_sprint:
        sprints = jira.sprints(board.id, extended=['startDate', 'endDate'], maxResults=max_results)
        if len(sprints) > 0:
            raise Exception('There\'s no open sprint')
        last_sprint = sprints[-1]
        jira.add_issues_to_sprint(last_sprint.id, )


def parse_issues(src):
    with open(src, 'rt') as src_file:
        lines = list(src_file.readlines())
    issue_dicts = []
    curr_issue = None
    for line in lines:
        line = line.strip()
        if len(line) == 0:
            continue
        code = line[0]
        text = line[1:].strip()
        if code == '-':
            if len(text) == 0:
                print('skipping empty task')
                continue
            if '(X)' in text:
                text = text.replace('(X)', '').strip()
                add_to_sprint = True
            else:
                add_to_sprint = False
            curr_issue = dict(summary=text, sub_issues=[], description='', add_to_sprint=add_to_sprint)
            issue_dicts.append(curr_issue)
        elif code == '+':
            if len(text) == 0:
                print('skipping empty sub-task')
                continue
            sub_issue = dict(summary=text, sub_issues=[], description='')
            curr_issue['sub_issues'].append(sub_issue)
        elif code == '*':
            if curr_issue is None:
                print('no task associated with description \'{}\''.format(text))
                continue
            if len(text) == 0:
                print('skipping empty description')
                continue
            curr_issue['description'] += '* {}\n'.format(text)
    return issue_dicts


def text2jira(*, src, server_url, basic_auth, board_name, assignee_key, components, max_results=MAX_RESULTS):
    issue_dicts = parse_issues(src)
    create_issues_in_jira(issue_dicts=issue_dicts,
                          server_url=server_url,
                          basic_auth=basic_auth,
                          board_name=board_name,
                          assignee_key=assignee_key,
                          components=components,
                          max_results=max_results)


_DB = 'text2jira.db'


def _get_db_connection():
    conn = sqlite3.connect(_DB, isolation_level=None)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='server_conns'")
    results = cur.fetchall()
    if not results:
        conn.execute('''CREATE TABLE server_conns
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url VARCHAR(100) NOT NULL,
                        user VARCHAR(100) NOT NULL,
                        password VARCHAR(100) NOT NULL)''')
    return conn


class AddServerConnDialog:
    def __init__(self, parent):
        self._top = tk.Toplevel(parent)
        self._top.resizable(width=False, height=False)
        self._top.geometry('{}x{}'.format(220, 155))
        tk.Label(self._top, text='URL').pack()
        self._url = tk.StringVar()
        tk.Entry(self._top, textvariable=self._url).pack(padx=5)
        tk.Label(self._top, text='User').pack()
        self._user = tk.StringVar()
        tk.Entry(self._top, textvariable=self._user).pack(padx=5)
        tk.Label(self._top, text='Password').pack()
        self._password = tk.StringVar()
        tk.Entry(self._top, show='*', textvariable=self._password).pack(padx=5)
        self._ok_button = tk.Button(self._top, text='OK', command=self.on_ok)
        self._ok_button.pack(pady=5)

    def on_init(self):
        pass

    @property
    def url(self):
        return self._url.get()

    @property
    def user(self):
        return self._user.get()

    @property
    def password(self):
        return self._password.get()

    def on_ok(self):
        self._top.destroy()

    @classmethod
    def show_modal(cls, parent, *args, **kwargs):
        obj = cls(parent, *args, **kwargs)
        parent.wait_window(obj._top)
        return obj


class RemoveServerConnDialog:
    def __init__(self, parent):
        self._top = tk.Toplevel(parent)
        self._top.resizable(width=False, height=False)
        self._top.geometry('{}x{}'.format(220, 160))
        self._servers_listbox = tk.Listbox(self._top, selectmode='single', width=200, height=5)
        self._servers_listbox.pack(padx=5, pady=5)
        self._servers_listbox.bind('<<ListboxSelect>>', self.on_select_server_from_listbox)
        self._ok_button = tk.Button(self._top, text='Find', command=self.on_find_servers)
        self._ok_button.pack(padx=5, pady=5)
        self._remove_button = tk.Button(self._top, text='Remove', command=self.on_remove_server, state='disabled')
        self._remove_button.pack()
        self._servers_idxs = []
        self.update_servers_listbox()

    def update_servers_listbox(self):
        del self._servers_idxs[:]
        conn = _get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, url FROM server_conns')
        for row in cur:
            self._servers_idxs.append(row[0])
            self._servers_listbox.insert('end', row[1])

    def on_find_servers(self):
        self.clear_controls()
        self.update_servers_listbox()

    def on_remove_server(self):
        self._remove_button.config(state='disabled')
        idx = int(self._servers_listbox.curselection()[0])
        self._servers_listbox.delete(idx)
        conn = _get_db_connection()
        conn.execute('DELETE FROM server_conns WHERE id = ?', (self._servers_idxs[idx],))
        del self._servers_idxs[idx]

    def on_select_server_from_listbox(self, evt):
        self._remove_button.config(state='active')

    def clear_controls(self):
        self._remove_button.config(state='disabled')
        self._servers_listbox.delete(0, 'end')

    @classmethod
    def show_modal(cls, parent, *args, **kwargs):
        obj = cls(parent, *args, **kwargs)
        parent.wait_window(obj._top)
        return obj


class Text2JiraGUI(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self._master = master
        self._master.wm_title('text2jira')
        self._master.resizable(width=False, height=False)
        self._master.geometry('{}x{}'.format(300, 325))
        menu_bar = tk.Menu(self._master)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label='Load', command=self.on_load)
        file_menu.add_command(label='Run', command=self.on_run)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self._master.quit)
        menu_bar.add_cascade(label='File', menu=file_menu)
        server_conn_menu = tk.Menu(menu_bar, tearoff=0)
        server_conn_menu.add_command(label='Add', command=self.on_add_server_conn)
        server_conn_menu.add_command(label='Remove', command=self.on_remove_server_conn)
        menu_bar.add_cascade(label='Server Connection', menu=server_conn_menu)
        self._master.config(menu=menu_bar)
        tk.Label(self, text='Server Connection').pack()
        self._servers_combobox = ttk.Combobox(self, width=200)
        self._servers_combobox.pack(padx=5, pady=5)
        tk.Label(self, text='Board').pack()
        self._board_name = tk.StringVar()
        tk.Entry(self, textvariable=self._board_name, width=200).pack(padx=5, pady=5)
        tk.Label(self, text='Assignee').pack()
        self._assignee_key = tk.StringVar()
        tk.Entry(self, textvariable=self._assignee_key, width=200).pack(padx=5, pady=5)
        tk.Label(self, text='Components').pack()
        self._components = tk.StringVar()
        tk.Entry(self, textvariable=self._components, width=200).pack(padx=5, pady=5)
        tk.Label(self, text='Filename').pack()
        self._filename = tk.StringVar()
        tk.Entry(self, textvariable=self._filename, state='disabled', width=200).pack(padx=5, pady=5)
        tk.Button(self, text='Load', command=self.on_load).pack(padx=5, pady=5)
        tk.Button(self, text='Run', command=self.on_run).pack(padx=5, pady=5)
        self._server_conns = []
        self.update_servers_combobox()
        self.pack()

    def on_select_server_from_combobox(self, evt):
        pass

    def update_servers_combobox(self):
        conn = _get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT url, user, password FROM server_conns')
        servers = []
        for row in cur:
            self._server_conns.append(dict(url=row[0], user=row[1], password=row[2]))
            servers.append(row[0])
        self._servers_combobox['values'] = servers

    def on_remove_server_conn(self):
        RemoveServerConnDialog.show_modal(self._master)
        self.update_servers_combobox()

    def on_add_server_conn(self):
        dialog = AddServerConnDialog.show_modal(self._master)
        conn = _get_db_connection()
        conn.execute('INSERT INTO server_conns (url, user, password) VALUES (?, ?, ?)', (dialog.url,
                                                                                         dialog.user,
                                                                                         dialog.password))
        self.update_servers_combobox()

    def on_load(self):
        filename = askopenfilename(parent=self._master)
        if filename:
            self._filename.set(filename)

    def on_run(self):
        server_conn_idx = self._servers_combobox.current()
        if server_conn_idx == -1:
            showerror('Error', 'You need to select a server connection')
            return
        else:
            server_dict = self._server_conns[server_conn_idx]
            server_url = server_dict['url']
            basic_auth = [server_dict['user'], server_dict['password']]

        board_name = self._board_name.get()
        if not board_name:
            showerror('Error', 'You need to inform a board')
            return

        assignee_key = self._assignee_key.get()
        if not assignee_key:
            showerror('Error', 'You need to inform an assignee')
            return

        if self._components.get():
            components = [component.strip() for component in self._components.get().split(',')]
        else:
            components = None

        src = self._filename.get()
        if not src:
            showerror('Error', 'You need to inform an filename')
            return

        try:
            text2jira(src=src,
                      server_url=server_url,
                      basic_auth=basic_auth,
                      board_name=board_name,
                      assignee_key=assignee_key,
                      components=components)
            showinfo('Info', 'text2jira ran successfully')
        except Exception as e:
            traceback.print_exc()
            showerror('Error', str(e))


def main():
    def _str_to_bool(value):
        assert value is not None
        return {'true': True, '1': True}.get(value.lower(), False)

    parser = argparse.ArgumentParser()
    parser.add_argument('--src', type=str, required=False, help='')
    parser.add_argument('--server_url', type=str, required=False, help='server URL')
    parser.add_argument('--basic_auth', type=str, nargs=2, required=False, help='username and password')
    parser.add_argument('--board_name', type=str, required=False, help='board name')
    parser.add_argument('--assignee_key', type=str, required=False, help='assignee key')
    parser.add_argument('--components', type=str, nargs='*', required=False, help='components')
    parser.add_argument('--no-gui', type=_str_to_bool, required=False, default=False)
    args = parser.parse_args()
    if args.no_gui:
        if args.src is None:
            print('src cannot be None')
            exit(-1)

        if args.server is None:
            print('server cannot be None')
            exit(-1)

        if args.basic_auth is None:
            print('basic_auth cannot be None')
            exit(-1)

        if args.assignee_key is None:
            print('assignee_key cannot be None')
            exit(-1)

        try:
            text2jira(src=args.src,
                      server_url=args.server_url,
                      basic_auth=args.basic_auth,
                      board_name=args.board_name,
                      assignee_key=args.assignee_key,
                      components=args.components)
        except Exception as e:
            print(str(e))
    else:
        root = tk.Tk()
        app = Text2JiraGUI(root)
        app.mainloop()

    exit(0)


if __name__ == '__main__':
    main()
