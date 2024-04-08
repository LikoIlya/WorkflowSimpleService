from typing import Literal

from rule_engine import Context, Rule

from .base import NodeBase, NodeType
from .body.condition import ConditionNodeBody
from .message import MessageNode

RuleAttributeContext = Context()


class ConditionNode(NodeBase, ConditionNodeBody):
    """Represents a node in a workflow that evaluates a condition.
    Condition nodes could have multiple inputs,
    but only two outputs: "No" or "Yes".
    Conditions are evaluated based on a rule.


    """

    _type = NodeType.condition
    color = "red"

    @property
    def __rule_statement__(self) -> Rule:
        """Prepared `Rule` instance from `self.rule` - rule statement string


        :returns: Rule - Prepared rule_engine.Rule instance

        """
        return Rule(self.rule, context=RuleAttributeContext)

    def execute_condition(
        self, last_message: MessageNode
    ) -> Literal["Yes", "No"]:
        """Executes the condition for the node.

        :param last_message: The last message received.
        :type last_message: MessageNode
        :param last_message: MessageNode:
        :param last_message: MessageNode:
        :param last_message: MessageNode:
        :returns: Yes" if the condition is met, "No" otherwise.
        :rtype: Literal["Yes", "No"]

        """
        if self.__rule_statement__.matches(
            last_message.model_dump(mode="json")
        ):
            return "Yes"
        else:
            return "No"
