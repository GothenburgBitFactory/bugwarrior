import inspect
import os
import sys

from jinja2 import Template

from bugwarrior.services import Issue


def make_table(grid):
    """ Make a RST-compatible table

    From http://stackoverflow.com/a/12539081

    """
    cell_width = 2 + max(
        reduce(
            lambda x, y: x+y, [[len(item) for item in row] for row in grid], []
        )
    )
    num_cols = len(grid[0])
    rst = table_div(num_cols, cell_width, 0)
    header_flag = 1
    for row in grid:
        rst = rst + '| ' + '| '.join(
            [normalize_cell(x, cell_width-1) for x in row]
        ) + '|\n'
        rst = rst + table_div(num_cols, cell_width, header_flag)
        header_flag = 0
    return rst


def table_div(num_cols, col_width, header_flag):
    if header_flag == 1:
        return num_cols*('+' + (col_width)*'=') + '+\n'
    else:
        return num_cols*('+' + (col_width)*'-') + '+\n'


def normalize_cell(string, length):
    return string + ((length - len(string)) * ' ')


def import_by_path(name):
    m = __import__(name)
    for n in name.split(".")[1:]:
        m = getattr(m, n)
    return m


def row_comparator(left_row, right_row):
    left = left_row[0]
    right = right_row[0]
    if left > right:
        return 1
    elif right > left or left == 'Field Name':
        return -1
    return 0


TYPE_NAME_MAP = {
    'date': 'Date & Time',
    'numeric': 'Numeric',
    'string': 'Text (string)',
    'duration': 'Duration'
}


if __name__ == '__main__':
    service = sys.argv[1]
    module = import_by_path(
        'bugwarrior.services.{service}'.format(service=service)
    )
    rows = []
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, Issue):
            for field_name, details in obj.UDAS.items():
                rows.append(
                    [
                        '``%s``' % field_name,
                        ' '.join(details['label'].split(' ')[1:]),
                        TYPE_NAME_MAP.get(
                            details['type'],
                            '``%s``' % details['type'],
                        ),
                    ]
                )

    rows = sorted(rows, cmp=row_comparator)
    rows.insert(0, ['Field Name', 'Description', 'Type'])

    filename = os.path.join(os.path.dirname(__file__), 'service_template.html')
    with open(filename) as template:
        rendered = Template(template.read()).render({
            'service_name_humane': service.title(),
            'service_name': service,
            'uda_table': make_table(rows)
        })

    print rendered
