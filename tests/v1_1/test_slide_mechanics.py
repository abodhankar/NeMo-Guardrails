# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test the core flow mechanics"""
import copy
import logging

from rich.logging import RichHandler

from nemoguardrails.colang.v1_1.runtime.statemachine import (
    InternalEvent,
    run_to_completion,
)
from tests.utils import _init_state, is_data_in_events

FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.DEBUG,
    format=FORMAT,
    datefmt="[%X,%f]",
    handlers=[RichHandler(markup=True)],
)

start_main_flow_event = InternalEvent(name="StartFlow", arguments={"flow_id": "main"})


def test_while_loop_mechanic():
    """"""

    content = """
    flow main

      while $ref is None
        match UtteranceUserAction().Finished(final_transcript="End") as $ref
        start UtteranceBotAction(script="Test")

      start UtteranceBotAction(script="Done")
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "End",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Test",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "Done",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


# TODO: Think about how to add back duplicate removal in normalization
# def test_start_and_grouping():
#     """"""

#     content = """
#     flow bot say $script
#       await UtteranceBotAction(script=$script)

#     flow main
#         start bot say "A"
#           and bot say "B"
#           and UtteranceBotAction(script="C")
#           and bot say "A"
#     """

#     state = run_to_completion(_init_state(content), start_main_flow_event)
#     assert is_data_in_events(
#         state.outgoing_events,
#         [
#             {
#                 "type": "StartUtteranceBotAction",
#                 "script": "A",
#             },
#             {
#                 "type": "StartUtteranceBotAction",
#                 "script": "B",
#             },
#             {
#                 "type": "StartUtteranceBotAction",
#                 "script": "C",
#             },
#             {
#                 "type": "StopUtteranceBotAction",
#             },
#             {
#                 "type": "StopUtteranceBotAction",
#             },
#             {
#                 "type": "StopUtteranceBotAction",
#             },
#         ],
#     )


def test_match_and_grouping():
    """"""

    content = """
    flow bot say $script
      await UtteranceBotAction(script=$script)

    flow main
        start bot say "A" as $ref_a
          and bot say "B" as $ref_b
          and UtteranceBotAction(script="C") as $ref_c
        match $ref_a.Finished()
          and $ref_b.Finished()
          and $ref_c.Finished()
        start bot say "Done"
    """

    state = run_to_completion(_init_state(content), start_main_flow_event)
    events = copy.deepcopy(state.outgoing_events)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "A",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "B",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "C",
            },
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceBotActionFinished",
            "final_script": "A",
            "action_uid": events[0]["action_uid"],
        },
    )
    assert is_data_in_events(state.outgoing_events, [])
    state = run_to_completion(
        state,
        {
            "type": "UtteranceBotActionFinished",
            "final_script": "B",
            "action_uid": events[1]["action_uid"],
        },
    )
    assert is_data_in_events(state.outgoing_events, [])
    state = run_to_completion(
        state,
        {
            "type": "UtteranceBotActionFinished",
            "final_script": "C",
            "action_uid": events[2]["action_uid"],
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Done",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_start_or_grouping():
    """"""

    content = """
    flow bot say $script
      await UtteranceBotAction(script=$script)

    flow main
        $number = 0
        while $number < 10
          start bot say "Hi"
            or bot say "Hello"
            or bot say "Welcome"
          $number = $number + 1
        await bot say "Done"
    """

    state = run_to_completion(_init_state(content), start_main_flow_event)
    assert len(state.outgoing_events) == 11


def test_await_or_grouping():
    """"""

    content = """
    flow user said $transcript
      match UtteranceUserAction().Finished(final_transcript=$transcript)

    flow main
        await user said "A"
          or UtteranceBotAction(script="B")
          or user said "C"
        start UtteranceBotAction(script="Match")
    """

    state = run_to_completion(_init_state(content), start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "B",
            }
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "A",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "Match",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )
    state = run_to_completion(_init_state(content), start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "B",
            }
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceBotActionFinished",
            "final_script": "B",
            "action_uid": state.outgoing_events[0]["action_uid"],
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Match",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )
    state = run_to_completion(_init_state(content), start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "B",
            }
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "C",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "Match",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_await_or_group_finish():
    """"""

    content = """
    flow bot say $text
      # meta: exclude from llm
      await UtteranceBotAction(script=$text) as $action

    flow bot express greeting
      bot say "Hi there!"
        or bot say "Welcome!"

    flow main
      bot express greeting
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
            }
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceBotActionFinished",
            "final_script": state.outgoing_events[0]["script"],
            "action_uid": state.outgoing_events[0]["action_uid"],
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )


def test_await_and_or_grouping():
    """"""

    content = """
    flow user said $transcript
      match UtteranceUserAction().Finished(final_transcript=$transcript)

    flow main
        await (user said "A" and user said "B")
          or (user said "C" and user said "D")
        start UtteranceBotAction(script="Match")
    """

    state = run_to_completion(_init_state(content), start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "A",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "C",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "B",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Match",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )

    state = run_to_completion(_init_state(content), start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "B",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "C",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "D",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Match",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_await_multimodal_action():
    """"""

    content = """
    flow bot say $text
      await UtteranceBotAction(script=$text) as $action

    flow bot gesture $gesture
      await GestureBotAction(gesture=$gesture) as $action

    flow bot express $text
      await bot say $text

    flow main
        start bot express "Hi"
        start bot gesture "Wave"
        match UtteranceUserAction().Finished()
    """

    state = run_to_completion(_init_state(content), start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Hi",
            },
            {
                "type": "StartGestureBotAction",
                "gesture": "Wave",
            },
        ],
    )


def test_activate_and_grouping():
    """"""

    content = """
    flow a
      start UtteranceBotAction(script="A")
      match UtteranceUserAction().Finished(final_transcript="a")

    flow b
      start UtteranceBotAction(script="B")
      match UtteranceUserAction().Finished(final_transcript="b")

    flow main
        activate a and b
        match UtteranceUserAction().Finished(final_transcript="end")
    """

    state = run_to_completion(_init_state(content), start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "A",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "B",
            },
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "a",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "A",
            },
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "b",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "B",
            },
        ],
    )


def test_if_branching_mechanic():
    """"""

    content = """
    flow main
      while $action_ref_3 is None
        if $event_ref_1 is None
          start UtteranceBotAction(script="Action1") as $event_ref_1
        else if $event_ref_2 is None
          start UtteranceBotAction(script="Action2") as $event_ref_2
        else
          start UtteranceBotAction(script="ActionElse") as $action_ref_3
        start UtteranceBotAction(script="Next")
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Action1",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "Next",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "Action2",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "Next",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "ActionElse",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "Next",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_event_reference_member_access():
    """"""

    content = """
    flow main
      match UtteranceUserAction().Finished() as $ref
      start UtteranceBotAction(script=$ref.arguments.final_transcript)
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "Hi there!",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Hi there!",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_action_reference_member_access():
    """"""

    content = """
    flow main
      start UtteranceBotAction(script="Hello") as $ref
      start UtteranceBotAction(script=$ref.start_event_arguments.script)
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Hello",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "Hello",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_flow_references_member_access():
    """"""

    content = """
    flow bot say $text
      start UtteranceBotAction(script=$text) as $action_ref

    flow main
      start bot say "Hello" as $flow_ref
      start UtteranceBotAction(script=$flow_ref.context.action_ref.start_event_arguments.script)
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Hello",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "Hello",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_values_in_strings():
    """"""

    content = """
    flow main
      start UtteranceBotAction(script="Roger") as $ref
      start UtteranceBotAction(script="Hi {{$ref.start_event_arguments.script}}!")
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Roger",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "Hi Roger!",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_flow_return_values():
    """"""

    content = """
    flow a
      return "success"

    flow b
      return 100

    flow c
      $result = "failed"
      return $result

    flow main
      $result_a = await a
      $result_b = await b
      $result_c = await c
      start UtteranceBotAction(script="{{$result_a}} {{$result_b}} {{$result_c}}")
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "success 100 failed",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_break_continue_statement_a():
    """"""

    content = """
    flow main
      $count = -1
      while True
        $count = $count + 1
        start UtteranceBotAction(script="S:{{$count}}")
        if $count < 1
          $count = $count
        elif $count < 3
          continue
        elif $count == 3
          break
        start UtteranceBotAction(script="E:{{$count}}")
      start UtteranceBotAction(script="Done")
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "S:0",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "E:0",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "S:1",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "S:2",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "S:3",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "Done",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_break_continue_statement_b():
    """"""

    content = """
    flow main
      while True
        start UtteranceBotAction(script="A")
        while True
          break
          start UtteranceBotAction(script="E1")
        start UtteranceBotAction(script="B")
        break
        start UtteranceBotAction(script="E2")
      start UtteranceBotAction(script="C")
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "A",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "B",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "C",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


# TODO: Stop actions/flows from cases that did not trigger in 'when' structure
def test_when_or_core_mechanics():
    """"""

    content = """
    flow user said $transcript
      match UtteranceUserAction.Finished(final_transcript=$transcript)

    flow main
      while True
        when UtteranceUserActionFinished(final_transcript="A")
          start UtteranceBotAction(script="A")
        orwhen UtteranceUserAction().Finished(final_transcript="B")
          start UtteranceBotAction(script="B")
        orwhen user said "C"
          start UtteranceBotAction(script="C")
          break
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "A",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "A",
            },
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "B",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "B",
            },
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "C",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "C",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_when_or_bot_action_mechanics():
    """"""

    content = """
    flow main
      while True
        when UtteranceBotAction(script="Happens immediately")
          start UtteranceBotAction(script="A")
        orwhen UtteranceUserActionFinished(final_transcript="B")
          start UtteranceBotAction(script="B")
          break
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Happens immediately",
            },
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceBotActionFinished",
            "final_script": "Happens immediately",
            "action_uid": state.outgoing_events[0]["action_uid"],
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "A",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "Happens immediately",
            },
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "B",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StartUtteranceBotAction",
                "script": "B",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_when_or_group_mechanics():
    """"""

    content = """
    flow user said $transcript
      match UtteranceUserAction.Finished(final_transcript=$transcript)

    flow main
      while True
        when UtteranceUserActionFinished(final_transcript="A")
          start UtteranceBotAction(script="A")
        orwhen (user said "B" and user said "C")
          start UtteranceBotAction(script="BC")
        orwhen (user said "D" or user said "E")
          start UtteranceBotAction(script="DE")
          break
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "A",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "A",
            },
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "B",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "C",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "BC",
            },
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "E",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "DE",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_when_or_competing_events_mechanics():
    """"""

    content = """
    flow user said something
      match UtteranceUserAction.Finished()

    flow user said $transcript
      match UtteranceUserAction.Finished(final_transcript=$transcript)

    flow main
      while True
        when user said "hello"
          start UtteranceBotAction(script="A")
        orwhen user said something
          start UtteranceBotAction(script="B")
        orwhen user said "hi"
          start UtteranceBotAction(script="C")
          break
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "hello",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "A",
            }
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "something 123",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "B",
            }
        ],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "hi",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "C",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


def test_abort_flow():
    """"""

    content = """
    flow a
      match UtteranceUserAction.Finished(final_transcript="go")
      abort
      start UtteranceBotAction(script="Error")

    flow main
      start a
      match FlowFailed(flow_id="a")
      start UtteranceBotAction(script="Success")
    """

    config = _init_state(content)
    state = run_to_completion(config, start_main_flow_event)
    assert is_data_in_events(
        state.outgoing_events,
        [],
    )
    state = run_to_completion(
        state,
        {
            "type": "UtteranceUserActionFinished",
            "final_transcript": "go",
        },
    )
    assert is_data_in_events(
        state.outgoing_events,
        [
            {
                "type": "StartUtteranceBotAction",
                "script": "Success",
            },
            {
                "type": "StopUtteranceBotAction",
            },
        ],
    )


if __name__ == "__main__":
    test_abort_flow()
