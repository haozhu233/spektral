from __future__ import print_function
from __future__ import unicode_literals

import glob
import inspect
import os
import re
import shutil
import sys

from spektral import chem
from spektral import brain
from spektral import datasets
from spektral import layers
from spektral import utils
from spektral.utils import plotting

try:
    reload(sys)
    sys.setdefaultencoding('utf8')
except NameError:
    pass


EXCLUDE = {}

# For each class to document, it is possible to:
# 1) Document only the class: [classA, classB, ...]
# 2) Document all its methods: [classA, (classB, "*")]
# 3) Choose which methods to document (methods listed as strings):
# [classA, (classB, ["method1", "method2", ...]), ...]
# 4) Choose which methods to document (methods listed as qualified names):
# [classA, (classB, [module.classB.method1, module.classB.method2, ...]), ...]

PAGES = [
    {
        'page': 'layers/convolution.md',
        'classes': [
            layers.GraphConv,
            layers.ChebConv,
            layers.GraphSageConv,
            layers.ARMAConv,
            layers.EdgeConditionedConv,
            layers.GraphAttention,
            layers.GraphConvSkip,
            layers.APPNP,
            layers.GINConv
        ]
    },
    {
        'page': 'layers/base.md',
        'functions': [],
        'methods': [],
        'classes': [
            layers.InnerProduct,
            layers.MinkowskiProduct
        ]
    },
    {
        'page': 'layers/pooling.md',
        'functions': [],
        'methods': [],
        'classes': [
            layers.TopKPool,
            layers.MinCutPool,
            layers.DiffPool,
            layers.SAGPool,
            layers.GlobalSumPool,
            layers.GlobalAvgPool,
            layers.GlobalMaxPool,
            layers.GlobalAttentionPool,
            layers.GlobalAttnSumPool
        ]
    },
    {
        'page': 'datasets/citation.md',
        'functions': [
            datasets.citation.load_data
        ],
        'methods': [],
        'classes': []
    },
    {
        'page': 'datasets/delaunay.md',
        'functions': [
            datasets.delaunay.generate_data
        ],
        'methods': [],
        'classes': []
    },
    {
        'page': 'datasets/qm9.md',
        'functions': [
            datasets.qm9.load_data
        ],
        'methods': [],
        'classes': []
    },
{
        'page': 'datasets/mnist.md',
        'functions': [
            datasets.mnist.load_data
        ],
        'methods': [],
        'classes': []
    },
    {
        'page': 'brain.md',
        'functions': [
            brain.get_fc_graphs
        ],
        'methods': [],
        'classes': []
    },
    {
        'page': 'chem.md',
        'functions': [
            chem.numpy_to_rdkit,
            chem.numpy_to_smiles,
            chem.rdkit_to_smiles,
            chem.sdf_to_nx,
            chem.nx_to_sdf,
            chem.validate_rdkit,
            chem.get_atomic_symbol,
            chem.get_atomic_num,
            chem.valid_score,
            chem.novel_score,
            chem.unique_score,
            chem.enable_rdkit_log,
            chem.plot_rdkit,
            chem.plot_rdkit_svg_grid
        ],
        'methods': [],
        'classes': []
    },
    {
        'page': 'utils/data.md',
        'classes': [
            utils.data.Batch
        ],
        'methods': [
            utils.data.Batch.get
        ]
    },
    {
        'page': 'utils/io.md',
        'functions': [
            utils.io.load_binary,
            utils.io.dump_binary,
            utils.io.load_csv,
            utils.io.dump_csv,
            utils.io.load_dot,
            utils.io.dump_dot,
            utils.io.load_npy,
            utils.io.dump_npy,
            utils.io.load_txt,
            utils.io.dump_txt,
            utils.io.load_sdf,
        ],
        'methods': [],
        'classes': []
    },
    {
        'page': 'utils/conversion.md',
        'functions': [
            utils.conversion.nx_to_adj,
            utils.conversion.nx_to_node_features,
            utils.conversion.nx_to_edge_features,
            utils.conversion.nx_to_numpy,
            utils.conversion.numpy_to_nx
        ],
        'methods': [],
        'classes': []
    },
    {
        'page': 'utils/convolution.md',
        'functions': [
            utils.convolution.degree,
            utils.convolution.degree_power,
            utils.convolution.normalized_adjacency,
            utils.convolution.laplacian,
            utils.convolution.normalized_laplacian,
            utils.convolution.localpooling_filter,
            utils.convolution.chebyshev_filter
        ],
        'methods': [],
        'classes': []
    },
    {
        'page': 'utils/misc.md',
        'functions': [
            utils.misc.batch_iterator,
            utils.misc.pad_jagged_array,
            utils.misc.add_eye,
            utils.misc.sub_eye,

        ],
        'methods': [],
        'classes': []
    },
    {
        'page': 'utils/plotting.md',
        'functions': [
            plotting.plot_numpy,
            plotting.plot_nx
        ],
        'methods': [],
        'classes': []
    }
]

ROOT = 'https://danielegrattarola.github.io/spektral/'


def get_function_signature(function, method=True):
    wrapped = getattr(function, '_original_function', None)
    if wrapped is None:
        try:
            signature = inspect.getargspec(function)
        except ValueError:
            signature = inspect.getfullargspec(function)
    else:
        signature = inspect.getargspec(wrapped)
    if signature.defaults is None:
        signature = signature._replace(defaults=[])
    defaults = signature.defaults
    if hasattr(signature, 'kwonlydefaults'):
        signature.args.extend(signature.kwonlyargs)
        for kwa in signature.kwonlyargs:
            defaults.append(signature.kwonlydefaults[kwa])
    if method:
        args = signature.args[1:]  # Remove self
    else:
        args = signature.args
    if defaults:
        kwargs = zip(args[-len(defaults):], defaults)
        args = args[:-len(defaults)]
    else:
        kwargs = []
    st = '%s.%s(' % (clean_module_name(function.__module__), function.__name__)

    for a in args:
        st += str(a) + ', '
    for a, v in kwargs:
        if isinstance(v, str):
            v = '\'' + v + '\''
        st += str(a) + '=' + str(v) + ', '
    if kwargs or args:
        signature = st[:-2] + ')'
    else:
        signature = st + ')'
    return post_process_signature(signature)


def get_class_signature(cls):
    try:
        class_signature = get_function_signature(cls.__init__)
        class_signature = class_signature.replace('__init__', cls.__name__)
    except (TypeError, AttributeError):
        # in case the class inherits from object and does not
        # define __init__
        class_signature = "{clean_module_name}.{cls_name}()".format(
            clean_module_name=clean_module_name(cls.__module__),
            cls_name=cls.__name__
        )
    return post_process_signature(class_signature)


def post_process_signature(signature):
    parts = re.split(r'\.(?!\d)', signature)
    if len(parts) >= 4:
        if parts[1] == 'layers':
            signature = 'spektral.layers.' + '.'.join(parts[3:])
        if parts[1] == 'utils':
            signature = 'spektral.utils.' + '.'.join(parts[3:])
    return signature


def clean_module_name(name):
    return name


def class_to_docs_link(cls):
    module_name = clean_module_name(cls.__module__)
    module_name = module_name[6:]
    link = ROOT + module_name.replace('.', '/') + '#' + cls.__name__.lower()
    return link


def class_to_source_link(cls):
    module_name = clean_module_name(cls.__module__)
    path = module_name.replace('.', '/')
    path += '.py'
    line = inspect.getsourcelines(cls)[-1]
    link = ('https://github.com/danielegrattarola/'
            'spektral/blob/master/' + path + '#L' + str(line))
    return '[[source]](' + link + ')'


def code_snippet(snippet):
    result = '```python\n'
    result += snippet + '\n'
    result += '```\n'
    return result


def count_leading_spaces(s):
    ws = re.search(r'\S', s)
    if ws:
        return ws.start()
    else:
        return 0


def process_list_block(docstring, starting_point, leading_spaces, marker):
    ending_point = docstring.find('\n\n', starting_point)
    block = docstring[starting_point:(None if ending_point == -1 else ending_point - 1)]
    # Place marker for later reinjection.
    docstring = docstring.replace(block, marker)
    lines = block.split('\n')
    # Remove the computed number of leading white spaces from each line.
    lines = [re.sub('^' + ' ' * leading_spaces, '', line) for line in lines]
    # Usually lines have at least 4 additional leading spaces.
    # These have to be removed, but first the list roots have to be detected.
    top_level_regex = r'^    ([^\s\\\(]+):(.*)'
    top_level_replacement = r'- __\1__:\2'
    lines = [re.sub(top_level_regex, top_level_replacement, line) for line in lines]
    # All the other lines get simply the 4 leading space (if present) removed
    lines = [re.sub(r'^    ', '', line) for line in lines]
    # Fix text lines after lists
    indent = 0
    text_block = False
    for i in range(len(lines)):
        line = lines[i]
        spaces = re.search(r'\S', line)
        if spaces:
            # If it is a list element
            if line[spaces.start()] == '-':
                indent = spaces.start() + 1
                if text_block:
                    text_block = False
                    lines[i] = '\n' + line
            elif spaces.start() < indent:
                text_block = True
                indent = spaces.start()
                lines[i] = '\n' + line
        else:
            text_block = False
            indent = 0
    block = '\n'.join(lines)
    return docstring, block


def process_docstring(docstring):
    # First, extract code blocks and process them.
    code_blocks = []
    if '```' in docstring:
        tmp = docstring[:]
        while '```' in tmp:
            tmp = tmp[tmp.find('```'):]
            index = tmp[3:].find('```') + 6
            snippet = tmp[:index]
            # Place marker in docstring for later reinjection.
            docstring = docstring.replace(snippet, '$CODE_BLOCK_%d' % len(code_blocks))
            snippet_lines = snippet.split('\n')
            # Remove leading spaces.
            num_leading_spaces = snippet_lines[-1].find('`')
            snippet_lines = ([snippet_lines[0]] +
                             [line[num_leading_spaces:]
                             for line in snippet_lines[1:]])
            # Most code snippets have 3 or 4 more leading spaces
            # on inner lines, but not all. Remove them.
            inner_lines = snippet_lines[1:-1]
            leading_spaces = None
            for line in inner_lines:
                if not line or line[0] == '\n':
                    continue
                spaces = count_leading_spaces(line)
                if leading_spaces is None:
                    leading_spaces = spaces
                if spaces < leading_spaces:
                    leading_spaces = spaces
            if leading_spaces:
                snippet_lines = ([snippet_lines[0]] +
                                 [line[leading_spaces:]
                                  for line in snippet_lines[1:-1]] +
                                 [snippet_lines[-1]])
            snippet = '\n'.join(snippet_lines)
            code_blocks.append(snippet)
            tmp = tmp[index:]

    # Format docstring lists.
    section_regex = r'\n( +)# (.*)\n'
    section_idx = re.search(section_regex, docstring)
    shift = 0
    sections = {}
    while section_idx and section_idx.group(2):
        anchor = section_idx.group(2)
        leading_spaces = len(section_idx.group(1))
        shift += section_idx.end()
        marker = '$' + anchor.replace(' ', '_') + '$'
        docstring, content = process_list_block(docstring,
                                                shift,
                                                leading_spaces,
                                                marker)
        sections[marker] = content
        section_idx = re.search(section_regex, docstring[shift:])

    # Format docstring section titles.
    docstring = re.sub(r'\n(\s+)# (.*)\n',
                       r'\n\1__\2__\n\n',
                       docstring)

    # Strip all remaining leading spaces.
    lines = docstring.split('\n')
    docstring = '\n'.join([line.lstrip(' ') for line in lines])

    # Reinject list blocks.
    for marker, content in sections.items():
        docstring = docstring.replace(marker, content)

    # Reinject code blocks.
    for i, code_block in enumerate(code_blocks):
        docstring = docstring.replace(
            '$CODE_BLOCK_%d' % i, code_block)

    # Spektral-specific code
    docstring = re.sub(r':param', '\n**Arguments**  \n:param', docstring, 1)
    docstring = re.sub(r':param(.*):', r'\n- `\1`:', docstring)
    docstring = re.sub(r':return: ([a-z])', lambda m: ':return: {}'.format(m.group(1).upper()), docstring)
    docstring = re.sub(r':return:', '\n**Return**  \n', docstring)

    return docstring


print('Cleaning up existing sources directory.')
if os.path.exists('sources'):
    shutil.rmtree('sources')

print('Populating sources directory with templates.')
for subdir, dirs, fnames in os.walk('templates'):
    for fname in fnames:
        new_subdir = subdir.replace('templates', 'sources')
        if not os.path.exists(new_subdir):
            os.makedirs(new_subdir)
        if fname[-3:] == '.md':
            fpath = os.path.join(subdir, fname)
            new_fpath = fpath.replace('templates', 'sources')
            shutil.copy(fpath, new_fpath)


def read_file(path):
    with open(path) as f:
        return f.read()


def collect_class_methods(cls, methods):
    if isinstance(methods, (list, tuple)):
        return [getattr(cls, m) if isinstance(m, str) else m for m in methods]
    methods = []
    for _, method in inspect.getmembers(cls, predicate=inspect.isroutine):
        if method.__name__[0] == '_' or method.__name__ in EXCLUDE:
            continue
        methods.append(method)
    return methods


def render_function(function, method=True):
    subblocks = []
    signature = get_function_signature(function, method=method)
    if method:
        signature = signature.replace(
            clean_module_name(function.__module__) + '.', '')
    subblocks.append('### ' + function.__name__ + '\n')
    subblocks.append(code_snippet(signature))
    docstring = function.__doc__
    if docstring:
        subblocks.append(process_docstring(docstring))
    return '\n\n'.join(subblocks)


def read_page_data(page_data, type):
    assert type in ['classes', 'functions', 'methods']
    data = page_data.get(type, [])
    for module in page_data.get('all_module_{}'.format(type), []):
        module_data = []
        for name in dir(module):
            if name[0] == '_' or name in EXCLUDE:
                continue
            module_member = getattr(module, name)
            if (inspect.isclass(module_member) and type == 'classes' or
               inspect.isfunction(module_member) and type == 'functions'):
                instance = module_member
                if module.__name__ in instance.__module__:
                    if instance not in module_data:
                        module_data.append(instance)
        module_data.sort(key=lambda x: id(x))
        data += module_data
    return data


if __name__ == '__main__':
    readme = read_file('../README.md')
    index = read_file('templates/index.md')
    # index = index.replace('{{autogenerated}}', readme[readme.find('##'):])
    index = index.replace('{{autogenerated}}', readme)
    with open('sources/index.md', 'w') as f:
        f.write(index)

    print('Generating docs for Spektral')
    for page_data in PAGES:
        classes = read_page_data(page_data, 'classes')

        blocks = []
        for element in classes:
            if not isinstance(element, (list, tuple)):
                element = (element, [])
            cls = element[0]
            subblocks = []
            signature = get_class_signature(cls)
            subblocks.append('<span style="float:right;">' +
                             class_to_source_link(cls) + '</span>')
            if element[1]:
                subblocks.append('## ' + cls.__name__ + ' class\n')
            else:
                subblocks.append('### ' + cls.__name__ + '\n')
            subblocks.append(code_snippet(signature))
            docstring = cls.__doc__
            if docstring:
                subblocks.append(process_docstring(docstring))
            methods = collect_class_methods(cls, element[1])
            if methods:
                subblocks.append('\n---')
                subblocks.append('## ' + cls.__name__ + ' methods\n')
                subblocks.append('\n---\n'.join(
                    [render_function(method, method=True) for method in methods]))
            blocks.append('\n'.join(subblocks))

        methods = read_page_data(page_data, 'methods')

        for method in methods:
            blocks.append(render_function(method, method=True))

        functions = read_page_data(page_data, 'functions')

        for function in functions:
            blocks.append(render_function(function, method=False))

        if not blocks:
            # raise RuntimeError('Found no content for page ' + page_data['page'])
            blocks = []

        mkdown = '\n----\n\n'.join(blocks)
        # save module page.
        # Either insert content into existing page,
        # or create page otherwise
        page_name = page_data['page']
        path = os.path.join('sources', page_name)
        if os.path.exists(path):
            template = read_file(path)
            assert '{{autogenerated}}' in template, ('Template found for ' + path +
                                                     ' but missing {{autogenerated}}'
                                                     ' tag.')
            mkdown = template.replace('{{autogenerated}}', mkdown)
            print('...inserting autogenerated content into template:', path)
        else:
            print('...creating new page with autogenerated content:', path)
        subdir = os.path.dirname(path)
        if not os.path.exists(subdir):
            os.makedirs(subdir)
        with open(path, 'w') as f:
            f.write(mkdown)
        if not os.path.exists('sources/stylesheets/'):
            os.makedirs('sources/stylesheets/')

        if not os.path.exists('sources/img/'):
            os.makedirs('sources/img/')

        if not os.path.exists('sources/custom_theme/img/'):
            os.makedirs('sources/custom_theme/img/')

        shutil.copy('./stylesheets/extra.css', './sources/stylesheets/extra.css')
        for file in glob.glob(r'./img/*.svg'):
            shutil.copy(file, './sources/img/')
        shutil.copy('./img/favicon.ico', './sources/custom_theme/img/favicon.ico')
        shutil.copy('./templates/google8a76765aa72fa8c1.html', './sources/google8a76765aa72fa8c1.html')
