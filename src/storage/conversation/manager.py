"""
Conversation Storage Manager

Manages conversation data storage including messages, tool calls, and statistics.
"""

import uuid

from sqlalchemy.orm import Session, joinedload

from src.storage.db.models import Conversation, ConversationStats, Message, ToolCall
from src.utils import logger
from src.utils.datetime_utils import utc_now


class ConversationManager:
    """Manager for conversation storage operations"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_conversation(
        self,
        user_id: str,
        agent_id: str,
        title: str | None = None,
        thread_id: str | None = None,
        metadata: dict | None = None,
    ) -> Conversation:
        """
        Create a new conversation

        Args:
            user_id: User ID
            agent_id: Agent ID
            title: Conversation title
            thread_id: Optional thread ID (will generate UUID if not provided)
            metadata: Optional additional metadata

        Returns:
            Created Conversation object
        """
        if not thread_id:
            thread_id = str(uuid.uuid4())

        conversation = Conversation(
            thread_id=thread_id,
            user_id=str(user_id),
            agent_id=agent_id,
            title=title or "New Conversation",
            status="active",
            extra_metadata=metadata if metadata else None,
        )

        self.db.add(conversation)
        # Flush to assign primary key without committing
        self.db.flush()

        # Create associated stats record and commit once
        stats = ConversationStats(conversation_id=conversation.id)
        self.db.add(stats)
        self.db.commit()
        self.db.refresh(conversation)

        logger.info(f"Created conversation: {conversation.thread_id} for user {user_id}")
        return conversation

    def get_conversation_by_thread_id(self, thread_id: str) -> Conversation | None:
        """
        Get conversation by thread ID

        Args:
            thread_id: Thread ID

        Returns:
            Conversation object or None if not found
        """
        return self.db.query(Conversation).filter(Conversation.thread_id == thread_id).first()

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        message_type: str = "text",
        extra_metadata: dict | None = None,
    ) -> Message:
        """
        Add a message to a conversation

        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant/system/tool)
            content: Message content
            message_type: Message type (text/tool_call/tool_result)
            extra_metadata: Additional metadata (complete message dump)

        Returns:
            Created Message object
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_type=message_type,
            extra_metadata=extra_metadata or {},
        )

        self.db.add(message)
        # Mark the parent conversation as active for sorting/analytics
        conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            conversation.updated_at = utc_now()

        self.db.commit()
        self.db.refresh(message)

        # Update conversation stats
        self._update_message_count(conversation_id)

        logger.debug(f"Added {role} message to conversation {conversation_id}")
        return message

    def add_message_by_thread_id(
        self,
        thread_id: str,
        role: str,
        content: str,
        message_type: str = "text",
        extra_metadata: dict | None = None,
    ) -> Message | None:
        """
        Add a message to a conversation by thread ID

        Args:
            thread_id: Thread ID
            role: Message role (user/assistant/system/tool)
            content: Message content
            message_type: Message type (text/tool_call/tool_result)
            extra_metadata: Additional metadata (complete message dump)

        Returns:
            Created Message object or None if conversation not found
        """
        conversation = self.get_conversation_by_thread_id(thread_id)
        if not conversation:
            logger.warning(f"Conversation not found for thread_id: {thread_id}")
            return None

        return self.add_message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            message_type=message_type,
            extra_metadata=extra_metadata,
        )

    def add_tool_call(
        self,
        message_id: int,
        tool_name: str,
        tool_input: dict | None = None,
        tool_output: str | None = None,
        status: str = "pending",
        error_message: str | None = None,
        langgraph_tool_call_id: str | None = None,
    ) -> ToolCall:
        """
        Add a tool call record

        Args:
            message_id: Message ID
            tool_name: Tool name
            tool_input: Tool input parameters
            tool_output: Tool execution result
            status: Status (pending/success/error)
            error_message: Error message if failed
            langgraph_tool_call_id: LangGraph tool_call_id for precise matching

        Returns:
            Created ToolCall object
        """
        tool_call = ToolCall(
            message_id=message_id,
            tool_name=tool_name,
            tool_input=tool_input or {},
            tool_output=tool_output,
            status=status,
            error_message=error_message,
            langgraph_tool_call_id=langgraph_tool_call_id,
        )

        self.db.add(tool_call)
        self.db.commit()
        self.db.refresh(tool_call)

        logger.debug(f"Added tool call {tool_name} to message {message_id}")
        return tool_call

    def get_messages(self, conversation_id: int, limit: int | None = None, offset: int = 0) -> list[Message]:
        """
        Get messages for a conversation

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of Message objects
        """
        query = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .options(joinedload(Message.tool_calls))
        )

        if limit:
            query = query.limit(limit).offset(offset)

        return query.all()

    def get_messages_by_thread_id(self, thread_id: str, limit: int | None = None, offset: int = 0) -> list[Message]:
        """
        Get messages for a conversation by thread ID

        Args:
            thread_id: Thread ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of Message objects
        """
        conversation = self.get_conversation_by_thread_id(thread_id)
        if not conversation:
            logger.warning(f"Conversation not found for thread_id: {thread_id}")
            return []

        return self.get_messages(conversation.id, limit, offset)

    def list_conversations(
        self, user_id: str | None = None, agent_id: str | None = None, status: str = "active"
    ) -> list[Conversation]:
        """
        List conversations for a user or all users

        Args:
            user_id: User ID (optional, if None or empty string, returns all users' conversations)
            agent_id: Optional agent ID filter
            status: Conversation status filter

        Returns:
            List of Conversation objects
        """
        query = self.db.query(Conversation).filter(Conversation.status == status)

        # Only filter by user_id if it's provided and not empty
        if user_id:
            query = query.filter(Conversation.user_id == str(user_id))

        if agent_id:
            query = query.filter(Conversation.agent_id == agent_id)

        return query.order_by(Conversation.updated_at.desc()).all()

    def update_conversation(
        self,
        thread_id: str,
        title: str | None = None,
        status: str | None = None,
        metadata: dict | None = None,
    ) -> Conversation | None:
        """
        Update conversation information

        Args:
            thread_id: Thread ID
            title: New title
            status: New status
            metadata: Additional metadata to merge

        Returns:
            Updated Conversation object or None if not found
        """
        conversation = self.get_conversation_by_thread_id(thread_id)
        if not conversation:
            return None

        if title is not None:
            conversation.title = title
        if status is not None:
            conversation.status = status

        # Handle metadata updates
        if metadata is not None:
            current_metadata = conversation.extra_metadata or {}
            current_metadata.update(metadata)
            conversation.extra_metadata = current_metadata

        conversation.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(conversation)

        logger.info(f"Updated conversation {thread_id}")
        return conversation

    def delete_conversation(self, thread_id: str, soft_delete: bool = True) -> bool:
        """
        Delete a conversation

        Args:
            thread_id: Thread ID
            soft_delete: If True, mark as deleted; if False, permanently delete

        Returns:
            True if successful, False otherwise
        """
        conversation = self.get_conversation_by_thread_id(thread_id)
        if not conversation:
            return False

        if soft_delete:
            conversation.status = "deleted"
            self.db.commit()
            logger.info(f"Soft deleted conversation {thread_id}")
        else:
            self.db.delete(conversation)
            self.db.commit()
            logger.info(f"Permanently deleted conversation {thread_id}")

        return True

    def batch_delete_conversations(self, thread_ids: list[str], soft_delete: bool = True) -> dict:
        """
        Batch delete conversations

        Args:
            thread_ids: List of thread IDs to delete
            soft_delete: If True, mark as deleted; if False, permanently delete

        Returns:
            Dictionary with success and failure counts
        """
        results = {
            "success_count": 0,
            "failed_count": 0,
            "failed_details": []
        }

        for thread_id in thread_ids:
            try:
                success = self.delete_conversation(thread_id, soft_delete)
                if success:
                    results["success_count"] += 1
                else:
                    results["failed_count"] += 1
                    results["failed_details"].append({
                        "thread_id": thread_id,
                        "reason": "删除失败"
                    })
            except Exception as e:
                results["failed_count"] += 1
                results["failed_details"].append({
                    "thread_id": thread_id,
                    "reason": str(e)
                })
                logger.error(f"批量删除对话 {thread_id} 失败: {e}")

        logger.info(f"批量删除完成: 成功 {results['success_count']}, 失败 {results['failed_count']}")
        return results

    def cleanup_deleted_conversations(self, days: int = 30) -> dict:
        """
        Clean up deleted conversations older than specified days

        Args:
            days: Number of days after which deleted conversations should be permanently removed

        Returns:
            Dictionary with cleanup results
        """
        from datetime import timedelta

        cutoff_date = utc_now() - timedelta(days=days)

        deleted_conversations = self.db.query(Conversation).filter(
            Conversation.status == "deleted",
            Conversation.updated_at < cutoff_date
        ).all()

        results = {
            "cleanup_count": 0,
            "failed_count": 0
        }

        for conv in deleted_conversations:
            try:
                # Hard delete the conversation and related data
                self.db.delete(conv)
                results["cleanup_count"] += 1
            except Exception as e:
                results["failed_count"] += 1
                logger.error(f"清理对话失败 {conv.thread_id}: {e}")

        self.db.commit()
        logger.info(f"清理完成: 成功 {results['cleanup_count']}, 失败 {results['failed_count']}")
        return results

    def get_stats(self, conversation_id: int) -> ConversationStats | None:
        """
        Get conversation statistics

        Args:
            conversation_id: Conversation ID

        Returns:
            ConversationStats object or None if not found
        """
        return self.db.query(ConversationStats).filter(ConversationStats.conversation_id == conversation_id).first()

    def update_stats(
        self,
        conversation_id: int,
        tokens_used: int | None = None,
        model_used: str | None = None,
        user_feedback: dict | None = None,
    ) -> ConversationStats | None:
        """
        Update conversation statistics

        Args:
            conversation_id: Conversation ID
            tokens_used: Number of tokens to add
            model_used: Model name
            user_feedback: User feedback data

        Returns:
            Updated ConversationStats object or None if not found
        """
        stats = self.get_stats(conversation_id)
        if not stats:
            return None

        if tokens_used is not None:
            stats.total_tokens += tokens_used
        if model_used is not None:
            stats.model_used = model_used
        if user_feedback is not None:
            stats.user_feedback = user_feedback

        stats.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(stats)

        return stats

    def get_tool_call_by_langgraph_id(self, langgraph_tool_call_id: str) -> ToolCall | None:
        """
        Get tool call by LangGraph tool_call_id

        Args:
            langgraph_tool_call_id: LangGraph tool_call_id

        Returns:
            ToolCall object or None if not found
        """
        return self.db.query(ToolCall).filter(ToolCall.langgraph_tool_call_id == langgraph_tool_call_id).first()

    def update_tool_call_output(
        self,
        langgraph_tool_call_id: str,
        tool_output: str,
        status: str = "success",
        error_message: str | None = None,
    ) -> ToolCall | None:
        """
        Update tool call output by LangGraph tool_call_id

        Args:
            langgraph_tool_call_id: LangGraph tool_call_id
            tool_output: Tool execution result
            status: Status (success/error)
            error_message: Error message if failed

        Returns:
            Updated ToolCall object or None if not found
        """
        tool_call = self.get_tool_call_by_langgraph_id(langgraph_tool_call_id)
        if not tool_call:
            logger.warning(f"Tool call not found for langgraph_tool_call_id: {langgraph_tool_call_id}")
            return None

        tool_call.tool_output = tool_output
        tool_call.status = status
        if error_message:
            tool_call.error_message = error_message

        self.db.commit()
        self.db.refresh(tool_call)

        logger.debug(f"Updated tool call {langgraph_tool_call_id} with output")
        return tool_call

    def _update_message_count(self, conversation_id: int) -> None:
        """
        Update message count in conversation stats

        Args:
            conversation_id: Conversation ID
        """
        stats = self.get_stats(conversation_id)
        if stats:
            message_count = self.db.query(Message).filter(Message.conversation_id == conversation_id).count()
            stats.message_count = message_count
            self.db.commit()
