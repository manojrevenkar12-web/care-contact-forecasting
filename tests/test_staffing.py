import numpy as np

from ccf.staffing.erlang import offered_load, required_agents, service_level


def test_erlang_c_matches_the_textbook_case():
    # 100 calls in half an hour at 6 minutes each is 20 Erlangs; 80% in 20 s needs 25 agents
    load = offered_load(np.array([100.0]), 360, 1800)
    assert load[0] == 20
    assert required_agents(load, 360, 20, 0.8)[0] == 25
    assert service_level(np.array([24]), load, 360, 20)[0] < 0.8 <= service_level(np.array([25]), load, 360, 20)[0]


def test_more_agents_never_lower_the_service_level():
    load = np.full(30, 12.0)
    sl = service_level(np.arange(10, 40), load, 300, 20)
    assert np.all(np.diff(sl) >= 0) and sl[0] == 0.0


def test_an_empty_interval_still_has_one_agent_and_full_service():
    assert required_agents(np.array([0.0]), 300, 20, 0.8)[0] == 1
    assert service_level(np.array([1]), np.array([0.0]), 300, 20)[0] == 1.0
