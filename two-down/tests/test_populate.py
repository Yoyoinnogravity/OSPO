from twodown.populate import CUT, ON_ICE, WAITING


def test_populate_bank_keeps_cut_films_and_waiting_aimlessly():
    assert "SMILES" in CUT
    assert "WELLINGTON" in CUT
    assert "AIMLESSLY" in CUT
    assert "DAVIS CUP" in ON_ICE
    assert WAITING[0] == "A GOGO"
    assert "AIMLESSLY" not in WAITING
