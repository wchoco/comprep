from typing import List, Union, Tuple, Optional
from pathlib import Path

from colorama import Fore, Style  # type: ignore

Entry = Union[str, Tuple[str, str]]


class Comprep:
    def __init__(self, name: str,
                 desc_fmt: str = "{choice:{length}s}: {desc}"
                 ) -> None:
        self.name = name
        self.data = []
        self.desc_fmt = desc_fmt
        self.title_color = Fore.CYAN + Style.BRIGHT

    def files(self, path: Optional[str] = None, ext: Optional[str] = None,
              ty: Optional[str] = None, hide_ext: bool = False,
              title: Optional[str] = None,
              include_hidden: bool = False) -> None:
        if path is None:
            path = "."
        glob = "*" if ext is None else f"*{ext}"
        targets = [p for p in Path(path).expanduser().glob(glob)]
        if ty is not None:
            if ty == "f":
                targets = [t for t in targets if t.is_file()]
            elif ty == "d":
                targets = [t for t in targets if t.is_dir()]
            else:
                raise ValueError(f"Unknown file type: {ty}")

        if not include_hidden:
            targets = [t for t in targets if not t.name.startswith(".")]

        choices: List[Entry] = [t.name for t in targets]
        if hide_ext:
            alt = [t.stem for t in targets]
        else:
            alt = None

        if title is None:
            title = f"Files in {path}"
        self.add(choices, alt=alt, title=title,
                 prefix=path.rstrip("/") + "/")
        self.set("files", [])
        self.register()

    def init(self, command: str, outdir: str = "."):
        template_path = Path(__file__).parent / "_comprep_template.zsh"
        with open(template_path) as fi:
            template = fi.read()
        out_path = Path(outdir) / f"_{self.name}"
        with open(out_path, "w") as fo:
            fo.write(template.format(command=self.name,
                                     comp_func=command))

    def add(self, choices: List[Entry],
            alt: Optional[List[str]] = None,
            title: Optional[Entry] = None,
            prefix: Optional[str] = None,
            suffix: Optional[str] = None,
            oneline: bool = False,
            ) -> None:

        comps = [c if isinstance(c, str) else c[0] for c in choices]
        if len(comps) == 0:
            return
        length = max(len(c) for c in comps)

        if alt is None:
            descs = [self.format_entry(c, length) for c in choices]
        else:
            if len(alt) != len(choices):
                raise ValueError("Length of alt differ from choices")
            entries = [a if isinstance(c, str) else (a, c[1])
                       for c, a in zip(choices, alt)]
            descs = [self.format_entry(e, length) for e in entries]

        self.data.clear()
        self.set("description", descs)
        if title is not None:
            self.set_title(title)
        if prefix is not None:
            self.set("prefix", [prefix])
        if suffix is not None:
            self.set("suffix", [suffix])
        if oneline:
            self.set("oneline", [])
        self.set("choices", comps)
        self.register()

    def format_entry(self, entry: Entry, length: int = 1) -> str:
        formatted = entry if isinstance(entry, str) \
            else self.desc_fmt.format(
            choice=entry[0],
            length=length,
            desc=entry[1])
        return formatted

    def register(self) -> None:
        print(len(self.data), *self.data, sep="\n")
        self.data.clear()

    def set(self, ty: str, args: List[str]) -> None:
        self.data.append(ty)
        self.data.append(len(args))
        self.data.extend(args)

    def set_title(self, title: Entry) -> None:
        self.set("title", [f"{self.title_color}{title}{Style.RESET_ALL}"])
