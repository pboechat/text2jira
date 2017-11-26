import argparse

from jira import JIRA

MAX_RESULTS = 100000


def create_issues_in_jira(*, issue_list, server, basic_auth, board_name, assignee_key, components, max_results):
    jira = JIRA(server=server, basic_auth=basic_auth)

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
    assert board
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

    issue_objs = []

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
        issue_objs.append(issue_obj)

    for issue in issue_list:
        _create_issue(issue)

    sprints = jira.sprints(board.id, extended=['startDate', 'endDate'], maxResults=max_results)
    assert len(sprints) > 0
    last_sprint = sprints[-1]

    jira.add_issues_to_sprint(last_sprint.id, [issue_obj.key for issue_obj in issue_objs])


def text2jira(*, src, server, basic_auth, board_name, assignee_key, components, max_results=MAX_RESULTS):
    with open(src, 'rt') as src_file:
        lines = list(src_file.readlines())
    issue_list = []
    curr_issue = None
    for line in lines:
        line = line.strip()
        if len(line) == 0:
            continue
        code = line[0]
        text = line[1:].strip()
        if code == '-':
            curr_issue = dict(summary=text, sub_issues=[], description='')
            issue_list.append(curr_issue)
        elif code == '+':
            sub_issue = dict(summary=text, sub_issues=[], description='')
            curr_issue['sub_issues'].append(sub_issue)
            curr_issue = sub_issue
        elif code == '*':
            if curr_issue is None:
                continue
            curr_issue['description'] += '* {}\n'.format(text)

    create_issues_in_jira(issue_list=issue_list,
                          server=server,
                          basic_auth=basic_auth,
                          board_name=board_name,
                          assignee_key=assignee_key,
                          components=components,
                          max_results=max_results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', type=str, required=True, help='')
    parser.add_argument('--server', type=str, required=True, help='server URL')
    parser.add_argument('--basic_auth', type=str, nargs=2, required=True, help='username and password')
    parser.add_argument('--board_name', type=str, required=True, help='board name')
    parser.add_argument('--assignee_key', type=str, required=True, help='assignee key')
    parser.add_argument('--components', type=str, nargs='*', required=False, help='components')
    args = parser.parse_args()
    text2jira(src=args.src,
              server=args.server,
              basic_auth=args.basic_auth,
              board_name=args.board_name,
              assignee_key=args.assignee_key,
              components=args.components)


if __name__ == '__main__':
    main()
