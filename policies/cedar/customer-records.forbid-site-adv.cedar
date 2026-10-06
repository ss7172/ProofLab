permit(
  principal,
  action == Action::"invoke",
  resource
) unless {
  context has toolName && !["customer-records___customer_lookup"].contains(context.toolName)
} unless {
  resource has dataClassification && resource.dataClassification == "restricted"
};

// ifabric D15(a) adversarial test rule v1 (DG-4). Additive and narrow: refuses only the declared test value SITE-ADV-*.
// Restore = customer-records.restore.cedar (byte-identical to the original). Applied only with the captain's OK at Hold-1.
forbid (
  principal,
  action == Action::"invoke",
  resource
) when {
  context has toolName && context.toolName == "customer-records___customer_lookup" &&
  context has arguments && context.arguments has site &&
  context.arguments.site like "SITE-ADV-*"
};
