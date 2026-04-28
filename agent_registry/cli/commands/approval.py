"""
Approval Command

Approve registered agents via UDS internal service.
"""

from argparse import ArgumentParser, Namespace

from agent_registry.cli import BaseCommand, CLI, Output
from agent_registry.cli.uds_client import get_uds_client


@CLI.register
class ApprovalCommand(BaseCommand):
    """Approve registered agent via internal UDS service"""

    @property
    def name(self) -> str:
        return "approval"

    @property
    def help_text(self) -> str:
        return "Approve registered agent (requires agent_approval_enabled=true)"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--agent-name", "-n", required=True, help="Agent name")
        parser.add_argument("--org", "-o", required=True, help="Organization name")
        parser.add_argument("--format", "-f", choices=["text", "json"], default="text")

    def execute(self, args: Namespace) -> int:
        output = Output(args.format)
        client = get_uds_client()
        
        result = client.approval_agent(args.agent_name, args.org)
        
        if args.format == "json":
            output.print(result)
            return 0 if result.get("success") else 1
        
        if result.get("success"):
            output.success(f"Agent '{args.agent_name}' approved successfully")
            if result.get("data"):
                data = result["data"]
                print(f"  Status: {data.get('status', 'published')}")
            return 0
        else:
            output.error(result.get("error", "Approval failed"))
            if result.get("message"):
                print(f"  Message: {result['message']}")
            return 1