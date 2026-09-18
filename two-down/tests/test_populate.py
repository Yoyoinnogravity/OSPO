from twodown.populate import CUT, ON_ICE, WAITING


def test_populate_bank_keeps_cut_films_and_waiting_aimlessly():
    assert "SMILES" in CUT
    assert "WELLINGTON" in CUT
    assert "DAVIS CUP" in ON_ICE
    assert WAITING[0] == "AIMLESSLY"
    assert "AIMLESSLY" not in CUT
    assert "AIMLESSLY" not in ON_ICE
