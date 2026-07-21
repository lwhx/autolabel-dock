"""DetectPoseView tests — keypoint-attach draw-state handling + seam guards.

The structural guards pin the 07-11 seam cleanup: the shell must drive views
through the TaskView contract (no hasattr sniffing), and DetectPoseView must
drive the canvas through public methods only (no `_canvas._*` private reach).
"""
import re
from collections import OrderedDict
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3] / "src"


def _make_view(qapp):
    from src.ui.views.detect_pose import DetectPoseView
    from src.utils.image import ImageCache

    return DetectPoseView(ImageCache(max_count=2, max_memory_mb=16.0), OrderedDict())


class TestKeypointAttachDrawState:
    def test_empty_draw_start_early_exits_and_clears_draw_state(self, qapp):
        from src.core.annotation import Annotation

        view = _make_view(qapp)
        try:
            ann = Annotation(class_name="cat", class_id=0, bbox=(0.5, 0.5, 0.3, 0.4))
            view._canvas.set_annotations([ann])
            # No pending draw-origin, but stale in-progress state exists.
            assert view._canvas.consume_draw_start() is None
            view._canvas._draw_current = (0.2, 0.2)

            view._on_keypoint_attach_requested(ann.id, 10.0, 10.0)

            assert ann.keypoints == []  # early exit — picker never opened
            assert view._canvas._draw_current is None  # draw state cleared
        finally:
            view.deleteLater()

    def test_unknown_annotation_consumes_draw_start(self, qapp):
        """Consume-at-entry: even on the ann-missing early exit, the pending
        draw-origin is taken and cleared so later events can't reuse it."""
        view = _make_view(qapp)
        try:
            view._canvas._draw_start = (0.4, 0.6)
            view._canvas._draw_current = (0.4, 0.6)

            view._on_keypoint_attach_requested("no-such-id", 10.0, 10.0)

            assert view._canvas.consume_draw_start() is None
            assert view._canvas._draw_current is None
        finally:
            view.deleteLater()


class TestSeamStructuralGuards:
    def test_label_panel_has_no_hasattr_sniffing(self):
        """The shell drives views through the TaskView contract (default
        no-op members) — hasattr view-type sniffing must not come back."""
        pattern = re.compile(r"hasattr\s*\(")
        text = (SRC_ROOT / "ui" / "label_panel.py").read_text(encoding="utf-8")
        offenders = [
            f"src/ui/label_panel.py:{lineno}: {line.strip()}"
            for lineno, line in enumerate(text.splitlines(), start=1)
            if pattern.search(line)
        ]
        assert not offenders, (
            "hasattr sniffing in the LabelPanel shell — add the member to the "
            "TaskView contract (default no-op) instead:\n" + "\n".join(offenders)
        )

    def test_detect_pose_has_no_canvas_private_reach(self):
        """DetectPoseView uses AnnotationCanvas public methods only —
        `_canvas._*` attribute touches must not come back."""
        pattern = re.compile(r"_canvas\._")
        text = (SRC_ROOT / "ui" / "views" / "detect_pose.py").read_text(encoding="utf-8")
        offenders = [
            f"src/ui/views/detect_pose.py:{lineno}: {line.strip()}"
            for lineno, line in enumerate(text.splitlines(), start=1)
            if pattern.search(line)
        ]
        assert not offenders, (
            "private canvas state reached from DetectPoseView — add/extend a "
            "public AnnotationCanvas method instead:\n" + "\n".join(offenders)
        )
