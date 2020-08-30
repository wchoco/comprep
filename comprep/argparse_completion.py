from typing import List, Optional, Tuple, Dict, Any, Union, Text, Sequence
import argparse
import re

from .comprep import Comprep, Entry

CompParams = Tuple[str, Dict[str, Any]]
_SubParsersAction = argparse._SubParsersAction  # type: ignore


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self,
                 prog: Optional[str] = None,
                 usage: Optional[str] = None,
                 description: Optional[str] = None,
                 epilog: Optional[str] = None,
                 parents: Sequence[argparse.ArgumentParser] = [],
                 formatter_class: Any = argparse.HelpFormatter,
                 prefix_chars: str = '-',
                 fromfile_prefix_chars: Optional[str] = None,
                 argument_default: Optional[str] = None,
                 conflict_handler: str = 'error',
                 add_help: bool = True,
                 allow_abbrev: bool = True):
        super().__init__(
            prog, usage, description, epilog, parents, formatter_class,
            prefix_chars, fromfile_prefix_chars, argument_default,
            conflict_handler, add_help, allow_abbrev)

        self.comprep = Comprep(self.prog)
        self._insert_complete()
        self._comp_data = {}
        self._is_completion = False
        self._completion_map = {}

    def _insert_complete(self) -> None:
        self.add_argument(
            "--comprep-prefix",
            action=CompleteAction,
            nargs="?",
            help=argparse.SUPPRESS,
        )
        self.add_argument(
            "--comprep-words",
            action=CompleteAction,
            nargs="?",
            help=argparse.SUPPRESS,
        )
        self.add_argument(
            "--init-completion",
            action=CompleteAction,
            nargs=0,
            help="Initialize completion file"
        )

    def set_completion_map(self, cmap: Dict[str, CompParams]):
        self._completion_map.update(cmap)

    def init_completion(self):
        prog = self.prog + (' --comprep-prefix \\"$PREFIX\\"'
                            ' --comprep-words "$words"')
        self.comprep.init(prog)

    def error(self, message: Text):
        if self._is_completion:
            if "init_completion" in self._comp_data:
                self.init_completion()
                return self.exit(0)
            self.complete(self._comp_data["comprep_words"].split()[1:])
            return self.exit(1)
        else:
            return super().error(message)

    def register_comp_data(self, key: str, value: Any):
        self._comp_data[key] = value

    def is_completion(self):
        self._is_completion = True

    def get_args_pattern(self, arg_strings: List[str]
                         ) -> Tuple[str,
                                    Dict[int, Tuple[argparse.Action, str]]]:
        """From cpython 3.8 argparse module definition"""
        option_string_indices = {}
        arg_string_pattern_parts = []
        arg_strings_iter = iter(arg_strings)
        for i, arg_string in enumerate(arg_strings_iter):

            # all args after -- are non-options
            if arg_string == '--':
                arg_string_pattern_parts.append('-')
                for arg_string in arg_strings_iter:
                    arg_string_pattern_parts.append('A')

            # otherwise, add the arg to the arg strings
            # and note the index if it was an option
            else:
                option_tuple = \
                    self._parse_optional(arg_string)
                if option_tuple is None:
                    pattern = 'A'
                else:
                    option_string_indices[i] = option_tuple
                    pattern = 'O'
                arg_string_pattern_parts.append(pattern)

        # join the pieces together to form the pattern
        arg_strings_pattern = ''.join(arg_string_pattern_parts)
        return arg_strings_pattern, option_string_indices

    def get_positional_actions(self, parser: argparse.ArgumentParser):
        return parser._get_positional_actions()

    def get_min_nargs(self, actions: List[argparse.Action]) -> int:
        min_nargs = 0
        for action in actions:
            nargs = action.nargs
            if isinstance(nargs, int):
                min_nargs += nargs
            elif nargs == "+":
                min_nargs += 1
        return min_nargs

    def get_possible_actions(self, parser: argparse.ArgumentParser,
                             arg_strings: List[str]
                             ) -> Tuple[List[argparse.Action],
                                        List[argparse.Action]]:
        possible = []
        if self._comp_data["comprep_prefix"] != "":
            arg_strings[:] = arg_strings[:-1]

        positionals = self.get_positional_actions(parser)
        arg_pat, opt_idx = self.get_args_pattern(arg_strings)

        if len(opt_idx) == 0:
            last_opt_idx = -1
        else:
            last_opt_idx = max(opt_idx)

        cursor = 0
        arg_end = len(arg_pat)

        # consume all optional actions
        opts = {o.dest: o for o in parser._get_optional_actions()
                if o.help != argparse.SUPPRESS}
        if "init_completion" in opts:
            opts.pop("init_completion")
        while cursor <= last_opt_idx:
            next_opt_idx = min([i for i in opt_idx if cursor <= i])
            if cursor == next_opt_idx:
                opt = opt_idx[next_opt_idx][0]
                opt_pat = self._get_nargs_pattern(opt)
                match = re.match(opt_pat, arg_pat[cursor+1:])
                opts.pop(opt.dest)
                if match is None:
                    if next_opt_idx == last_opt_idx:
                        possible.append(opt)
                        return possible, []
                    else:
                        raise ValueError
                cursor += match.end() + 1
                if cursor == arg_end and opt.nargs in ["*", "+"]:
                    possible.append(opt)
            else:
                for i in range(len(positionals), 0, -1):
                    pos_pat = "".join(
                        self._get_nargs_pattern(x) for x in positionals[:i])
                    match = re.match(pos_pat, arg_pat[cursor:])
                    pos_action = positionals[i-1]
                    if match is None:
                        continue
                    else:
                        if isinstance(pos_action, _SubParsersAction):
                            sub_span = match.span(i)
                            subcommand = arg_strings[cursor + sub_span[0]]
                            if subcommand in pos_action.choices:
                                return self.get_possible_actions(
                                    pos_action.choices[subcommand],
                                    arg_strings[cursor+sub_span[0]+1:])
                            else:
                                raise ValueError
                        cursor += match.end()
                        positionals[:] = positionals[i:]
                        break
        possible_opts = [o for _, o in opts.items()]

        # consume rest of postional actions
        for i in range(1, len(positionals)+1):
            pos_pat = "".join(
                self._get_nargs_pattern(x) for x in positionals[:i])
            match = re.match(pos_pat, arg_pat[cursor:])
            pos_action = positionals[i-1]
            if match is None:
                possible.append(pos_action)
                break
            elif cursor + match.end() == arg_end:
                min_nargs = self.get_min_nargs(positionals[:i])
                if pos_action.nargs in ["*", "+"]:
                    possible.append(pos_action)
                # if match.end() - match.start() < min_nargs:
                if min_nargs < match.end() - match.start():
                    possible.append(pos_action)
            if isinstance(pos_action, _SubParsersAction):
                sub_span = match.span(i)
                subcommand = arg_strings[cursor + sub_span[0]]
                if subcommand in pos_action.choices:
                    return self.get_possible_actions(
                        pos_action.choices[subcommand],
                        arg_strings[cursor+sub_span[0]+1:])
        return possible, possible_opts

    def complete(self, arg_strings: List[str],
                 parser: Optional[argparse.ArgumentParser] = None) -> None:
        if parser is None:
            parser = self

        pos, opts = self.get_possible_actions(
            parser, arg_strings)

        if self._comp_data["comprep_prefix"] not in ["-", "--"]:
            for p in pos:
                title = p.dest + ("" if p.help is None else f": {p.help}")

                if p.dest in self._completion_map:
                    cparams = self._completion_map[p.dest]
                    ty = cparams[0]
                    params = {"title": title}
                    params.update(cparams[1])

                    if ty == "list":
                        self.comprep.add(**params)
                    if ty == "files":
                        self.comprep.files(**params)
                    continue

                if isinstance(p, _SubParsersAction):
                    descs = [v.description for _, v in p.choices.items()]
                    comp = [(c, d) if d is not None else c for c,
                            d in zip(p.choices, descs)]
                    if p.dest == argparse.SUPPRESS:
                        title = "subcommand"
                    self.comprep.add(comp, title=title)
                elif p.choices is not None:
                    choices: List[Entry] = [str(c) for c in p.choices]
                    self.comprep.add(choices, title=title)
                else:
                    prefix = self._comp_data["comprep_prefix"]
                    self.comprep.files(
                        None if prefix == "" else prefix, title=title)

        if len(opts) > 0:
            opts_name: List[Entry] = [o.option_strings[0] for o in opts]
            alt = [f"{'|'.join(o.option_strings)}" +
                   ("" if o.help is None else f": {o.help}") for o in opts]
            self.comprep.add(choices=opts_name, alt=alt,
                             title="options", oneline=True)


class CompleteAction(argparse.Action):
    def __call__(self, parser: ArgumentParser,
                 namespace: argparse.Namespace,
                 values: Union[Text, Sequence[Any], None],
                 option_string: Optional[Text]
                 ) -> None:
        if isinstance(values, str):
            values = values.strip('"')
        parser.register_comp_data(self.dest, values)
        parser.is_completion()
