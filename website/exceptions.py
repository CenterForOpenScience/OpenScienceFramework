class OSFError(Exception):
    """Base class for exceptions raised by the Osf application"""
    pass


class NodeError(OSFError):
    """Raised when an action cannot be performed on a Node model"""
    pass


class NodeStateError(NodeError):
    """Raised when the Node's state is not suitable for the requested action

    Example: Node.remove_node() is called, but the node has non-deleted children
    """
    pass


class RetractionTokenError(NodeError):
    """Base class for errors arising from the user of a retraction token."""
    pass


class InvalidRetractionApprovalToken(RetractionTokenError):
    """Raised if a retraction approval token is not found."""
    message_short = "Invalid Token"
    message_long = "This retraction approval link is invalid."


class InvalidRetractionDisapprovalToken(RetractionTokenError):
    """Raised if a retraction disapproval token is not found."""
    message_short = "Invalid Token"
    message_long = "This retraction disapproval link is invalid."