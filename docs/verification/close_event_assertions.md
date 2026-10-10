# Close Event Assertion Comparison

Assertion comparison between baseline (`62c8db1`) and current multi-lane implementation (`HEAD`):

| Old Assertion (`62c8db1`) | New Assertion (`HEAD`) | Why Multi-Lane Design Needs This | At Least As Strict (yes/no) |
|---|---|---|---|
| `mock_mgr.cancel_active.assert_not_called()` | `v_mgr.shutdown.assert_called_once()`<br>`a_mgr.shutdown.assert_called_once()`<br>`mock_exec.assert_not_called()` | Both lanes are gracefully shut down to save persisted queue on close, without prompting the user. | yes |
| `mock_mgr.cancel_active.assert_not_called()` | `v_mgr.shutdown.assert_not_called()`<br>`a_mgr.shutdown.assert_not_called()`<br>`assert not event.isAccepted()` | When user clicks "Keep downloading", neither lane is shut down and the close event is ignored. | yes |
| `mock_mgr.cancel_active.assert_called_once()` | `v_mgr.shutdown.assert_called_once()`<br>`a_mgr.shutdown.assert_called_once()`<br>`assert actions[:2] == ["v_shutdown", "a_shutdown"]` | Closing must shut down BOTH independent lanes (video and audio) before waiting for workers to stop. | yes |
| `fake_worker.wait.assert_called_once_with(2000)` | `assert set(actions[2:]) == {"v_wait", "a_wait"}`<br>`assert len(timeouts) == 2`<br>`assert timeouts[1] < timeouts[0]`<br>`assert all(t <= 2000 for t in timeouts)` | Both workers share a single 2.0s deadline in total (`deadline = time.monotonic() + 2.0`). The second worker receives the remaining time slice, strictly decreasing and never exceeding 2000 ms. | yes |

## Strict Tests Added in Chunk 5

1. `test_close_cancels_both_lanes`: Verifies `shutdown()` is called on both video and audio managers when closing with active jobs.
2. `test_close_uses_one_shared_deadline`: Uses monkeypatched `time.monotonic` sequence (`itertools.count(0.0, 0.75)`) asserting that `wait()` on worker 2 receives a smaller timeout than worker 1, and all timeouts are `<= 2000` ms.
3. `test_close_with_no_active_jobs_does_not_ask`: Verifies that when both lanes are idle, the window closes immediately without showing any message box, while cleanly calling shutdown on both managers.
4. `test_close_rejected_leaves_both_lanes_running`: Verifies that clicking "Keep downloading" ignores the event and leaves both lane managers untouched.
