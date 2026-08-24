import unittest

from app.a2ui.envelope import SurfaceBuilder
from app.a2ui.validate import A2uiValidationError, validate_envelope


class TestSurfaceBuilder(unittest.TestCase):
    def test_build_produces_three_messages_for_one_surface(self):
        builder = SurfaceBuilder("test-surface", title="Test")
        builder.add("tile", "stat_tile", {"label": "L", "value": "V"})
        envelope = builder.build()

        self.assertEqual(len(envelope["messages"]), 3)
        types = [m["type"] for m in envelope["messages"]]
        self.assertEqual(
            types, ["createSurface", "updateComponents", "updateDataModel"]
        )
        for message in envelope["messages"]:
            self.assertEqual(message["surfaceId"], "test-surface")

    def test_add_attaches_child_to_parent(self):
        builder = SurfaceBuilder("s", title="T")
        builder.add("grid", "stat_grid")
        builder.add("tile", "stat_tile", {"label": "L", "value": "V"}, parent="grid")
        envelope = builder.build()

        components = {c["id"]: c for c in envelope["messages"][1]["components"]}
        self.assertIn("tile", components["grid"]["children"])

    def test_unknown_component_type_raises(self):
        builder = SurfaceBuilder("s", title="T")
        with self.assertRaises(ValueError):
            builder.add("bad", "not_a_real_type", {})

    def test_duplicate_component_id_raises(self):
        builder = SurfaceBuilder("s", title="T")
        builder.add("tile", "stat_tile", {"label": "L", "value": "V"})
        with self.assertRaises(ValueError):
            builder.add("tile", "stat_tile", {"label": "L2", "value": "V2"})

    def test_unknown_parent_raises(self):
        builder = SurfaceBuilder("s", title="T")
        with self.assertRaises(ValueError):
            builder.add(
                "tile", "stat_tile", {"label": "L", "value": "V"}, parent="nope"
            )

    def test_set_data_merges_into_data_model_message(self):
        builder = SurfaceBuilder("s", title="T")
        builder.set_data(foo="bar")
        builder.set_data(baz=1)
        envelope = builder.build()

        self.assertEqual(envelope["messages"][2]["data"], {"foo": "bar", "baz": 1})


class TestValidateEnvelope(unittest.TestCase):
    def _valid_envelope(self):
        builder = SurfaceBuilder("s", title="T")
        builder.add("tile", "stat_tile", {"label": "L", "value": "V"})
        return builder.build()

    def test_valid_envelope_passes(self):
        validate_envelope(self._valid_envelope())  # should not raise

    def test_missing_required_top_level_key_raises(self):
        envelope = self._valid_envelope()
        del envelope["catalogId"]
        with self.assertRaises(A2uiValidationError):
            validate_envelope(envelope)

    def test_unknown_message_type_raises(self):
        envelope = self._valid_envelope()
        envelope["messages"][0]["type"] = "notARealMessageType"
        with self.assertRaises(A2uiValidationError):
            validate_envelope(envelope)

    def test_multiple_surface_ids_raises(self):
        envelope = self._valid_envelope()
        envelope["messages"][0]["surfaceId"] = "other-surface"
        with self.assertRaises(A2uiValidationError):
            validate_envelope(envelope)

    def test_unknown_component_type_raises(self):
        envelope = self._valid_envelope()
        envelope["messages"][1]["components"][0]["type"] = "not_a_real_type"
        with self.assertRaises(A2uiValidationError):
            validate_envelope(envelope)

    def test_duplicate_component_id_raises(self):
        envelope = self._valid_envelope()
        components = envelope["messages"][1]["components"]
        dup = dict(components[0])
        components.append(dup)
        with self.assertRaises(A2uiValidationError):
            validate_envelope(envelope)

    def test_dangling_child_reference_raises(self):
        envelope = self._valid_envelope()
        envelope["messages"][1]["components"][0]["children"].append("does-not-exist")
        with self.assertRaises(A2uiValidationError):
            validate_envelope(envelope)

    def test_missing_root_component_raises(self):
        envelope = self._valid_envelope()
        components = envelope["messages"][1]["components"]
        envelope["messages"][1]["components"] = [
            c for c in components if c["id"] != "root"
        ]
        with self.assertRaises(A2uiValidationError):
            validate_envelope(envelope)


if __name__ == "__main__":
    unittest.main()
