from pathlib import Path

from scripts.isa_resolve import resolve
from scripts.degrade import Degradation, find_degradations

ISA_DIR = Path(__file__).resolve().parents[1] / "isa"
SIMPLE = resolve("Simple", ISA_DIR)
MADRID = resolve("Madrid", ISA_DIR)


def test_special_frame_degrades_when_target_lacks_specialframes():
    used = {"statementframe", "frame", "itemize"}
    out = find_degradations(used, source=SIMPLE, target=MADRID)
    instrs = {d.instruction for d in out}
    assert "statementframe" in instrs               # Madrid lacks SpecialFrames
    assert all(isinstance(d, Degradation) and d.lowering for d in out)
    assert "frame" not in instrs                     # frame is in Base, shared


def test_no_degradation_when_target_supports_everything_used():
    used = {"frame", "itemize", "block"}             # all in Base/Zsem, both themes share
    out = find_degradations(used, source=SIMPLE, target=MADRID)
    assert out == ()
