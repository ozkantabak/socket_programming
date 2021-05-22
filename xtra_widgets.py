try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk


class UnsupportedType(Exception):

    def __init__(self, failed_type=None):
        self.ft = failed_type

    def __str__(self):
        return "The {} data type is not supported. " \
               "Supported data types include int, str, float, list, tuple and bytes.".format(self.ft)


class ScrollBox(tk.LabelFrame):

    def __init__(self, master, relief='sunken', bd=2, width=20, height=10, **kwargs):
        super().__init__(master, relief=relief, bd=bd, **kwargs)

        self.list_box = tk.Listbox(self, width=width, height=height)
        self.v_scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.list_box.yview)
        self.h_scrollbar = tk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.list_box.xview)

    def grid(self, **kwargs):
        super().grid(**kwargs)
        self.list_box.grid(row=0, column=0, sticky='nsew')
        self.v_scrollbar.grid(row=0, column=1, sticky='nse')
        self.h_scrollbar.grid(row=1, column=0, sticky='new')
        self.list_box['yscrollcommand'] = self.v_scrollbar.set
        self.list_box['xscrollcommand'] = self.h_scrollbar.set

    def insert(self, index, *args):
        self.list_box.insert(index, *args)

    def special_insert(self, index, args: tuple):
        self.list_box.insert(index, *args)

    def clear(self):
        self.list_box.delete(0, tk.END)


class DBSearchBox(tk.LabelFrame):

    def __init__(self, master, connection, table=None, search_field=None,
                 show_fields=None, sql=None, pfilter=None, params=None,  # in pfilter use {sv} for the string var
                 relief='sunken', bd=2, width=20, height=10, **kwargs):
        super().__init__(master, relief=relief, bd=bd, **kwargs)

        self.cursor = connection.cursor()

        self.sql = sql
        self.pfilter = pfilter

        self.table = table
        self.search_field = search_field
        self.show_fields = show_fields

        self.sv = tk.StringVar(value='')
        self.scroll_box = ScrollBox(self, width=width, height=height)
        self.entry = tk.Entry(self, textvariable=self.sv)

    def grid(self, **kwargs):
        super().grid(**kwargs)
        self.entry.grid(row=0, column=0, sticky='ew')
        self.scroll_box.grid(row=1, column=0)

        self.sv.trace('w', lambda name, index, mode: self.search())
        self.search()

    def insert(self, *args):
        self.scroll_box.insert(*args)

    def clear(self):
        self.scroll_box.clear()

    def search(self):
        sql = ""
        pfilter = ""

        if self.sql:
            sql = self.sql
            pfilter = ' ' + self.pfilter.replace('{sv}', self.sv.get())
        else:
            sql = "SELECT {} FROM {}".format(str(self.show_fields).strip("()").replace("'", ''), self.table)
            # print(sql)
            pfilter = " WHERE {} LIKE '%{}%'".format(self.search_field, self.sv.get())
            # print(where)

        if self.sv.get():
            self.cursor.execute(sql + pfilter)
        else:
            self.cursor.execute(sql)

        self.clear()
        for value in self.cursor:
            self.insert(tk.END, ' | '.join(str(i) for i in value))


class NavigationBox(tk.LabelFrame):

    """
        Navigation Box: widget that lets you navigate through
    it's structure. It is, basically, a more organized ListBox.

                    ++ Structure ++
        The structure of a Navigation Box is defined by a dictionary
    similar to the following:

            {*page_id*: {*str_to_be_shown*: *command*}}

        + Rules +
            - The main page (first page to be shown) must have it's
              id = 0

            - The commands follow the following pattern:

                    *command_name* + '@' + *parameter(s)*

    ========================= Commands Available ===============================
    set_var@*type*, *value* -- sets internal variable to *value* of type *type*
                        goto@*id* -- goes to page *id*

            - Parameter MUST be separated by a COMMA ',' AND A SPACE ' '
     __________________________________________________________________________

        Let's say we want our navigation box to have the following
    structure:

            Main Page:
                -> 'Value 1'
                -> 'Folder 1' --goto Folder 1
                -> 'Folder 2' --goto Folder 2
            Folder 1:
                -> 'Value 2'
                -> 'Value hello'
            Folder 2:
                -> 'Value 4'
                -> 'Folder 3' --goto Folder 3
            Folder 3:
                -> 'Value 5'

        For the structure above, our dictionary would have to
    be:

        {0: {'Value 1': 'set_var@int, 1',
             'Folder 1': 'goto@1',
             'Folder 2': 'goto@2'},
         1: {'Value 2': 'set_var@int, 2',
             'Value hello': 'set_var@str, hello'},
         2: {'Value 4': 'set_var@int, 4',
             'Folder 3': 'goto@3'},
         3: {'Value 5': 'set_var@int, 5'}}

    ++++++++++++++++++++++++++++++++++++++++++++++++++++
    =================== Notes ==========================
    ++++++++++++++++++++++++++++++++++++++++++++++++++++

        In the set_var command you must specify the datatype
    of the value. Supported datatypes are:

            - int   (Integers)
            - float (Floating point numbers)
            - str   (Strings)
          § - list  (Lists, might not behave as expected,
                     see footnote.)
          § - tuple (Tuples, might not behave as expected,
                     see footnote.)
            - bytes (Bytes object)

        For unsupported data types it's recommended the use
    of the pickle module along with using bytes as the *type*
    parameter.

    § For those items marked with the '§' symbol.
      Marking the type as those datatypes might not generate
      the result you expect since a direct conversion of the
      *value* parameter is made(Eg.: 'list, [1, 2]' will
      generate ['[', '1', ',', ' ', '2', ']'] since list('[1, 2'])
      is equal to that). A way to get around that is using
      the pickle module, as seen above.

    """

    def __init__(self, master, structure: dict, size: tuple=(20, 10), **kwargs):
        super().__init__(master, **kwargs)

        self.known_commands = {'goto': self.goto,
                               'set_var': self.set_var}

        self.structure = structure

        self.scrollbox = ScrollBox(self, width=size[0], height=size[1])
        self.back_button = tk.Button(self, text=u'\u2b05',     # Unicode for <-
                                     command=self._back)

        self.cur_page_id = 0
        self.prev_page_history = []
        self.var = None

    def grid(self, **kwargs):
        super().grid(**kwargs)

        self.scrollbox.list_box.bind("<<ListboxSelect>>", self._on_select)
        self.goto((0, True))

        self.scrollbox.grid(row=1, column=0, sticky='nsew', columnspan=2)
        self.back_button.grid(row=0, column=0, sticky='nsw')
        self.back_button.config(state='disabled')

    def _on_select(self, event):
        if event.widget.curselection():
            index = event.widget.curselection()[0]
            selection = event.widget.get(index)
            statement = self.structure[self.cur_page_id][selection]

            command_str, parameters = statement.split('@')  # Separates command
            parameters = tuple(parameters.split(', '))      # Converts parameters to a tuple of STRs
            command = self.known_commands[command_str]      # Gets callable

            command(parameters)

    def goto(self, args: tuple):
        """
            §COMMAND

        ARGS: page_id, register
        DESC.:
            Goes to page with an id equal to page_id.
            Register is a bool, if set to False this goto will not
        be registered in self.prev_page_history
        """

        page_id = int(args[0]) if type(args[0]) == str else args[0]         # For external calls
        if len(args) > 1:                                                   # For external calls
            register = args[1]
        else:
            register = True                                                 # If the command is called from inside

        self.scrollbox.clear()
        self.scrollbox.special_insert(tk.END, tuple(self.structure[page_id].keys()))
        self.cur_page_id = page_id
        if register:
            self.prev_page_history.append(page_id)
            self.back_button.config(state='normal')

    def set_var(self, args: tuple):
        """
            §COMMAND

        ARGS: type, value
        DESC.:
            Sets internal variable (var) equal to value.
        """

        type_, value = args

        if type_ == 'str':
            pass                     # There's no need to convert to str
        elif type_ == 'int':
            value = int(value)
        elif type_ == 'float':
            value = float(value)
        elif type_ == 'list':
            value = list(value)
        elif type_ == 'tuple':
            value = tuple(value)
        elif type_ == 'bytes':
            value = bytes(value)
        else:
            raise UnsupportedType(type_)

        self.var = value
        print(self.var) # TODO: comment this line

    def _back(self):
        pid = self.prev_page_history[-2]
        self.prev_page_history.pop(-1)
        self.goto((pid, False))

        if len(self.prev_page_history) == 1:
            self.back_button.config(state='disabled')


if __name__ == "__main__":
    help(NavigationBox)
    r = tk.Tk()
    NavigationBox(r, {0: {'Value 1': 'set_var@int, 1',
                          "Folder 1>>": 'goto@1',
                          'Folder 2>>': 'goto@2'},
                      1: {'Value 2': 'set_var@int, 2',
                          'Value hello': 'set_var@dict, hello'},
                      2: {'Value 4': 'set_var@int, 4',
                          'Folder 3>>': 'goto@3'},
                      3: {'Value 5': 'set_var@str, 5'}}, text='Search').grid(row=1, column=1)
    r.mainloop()
