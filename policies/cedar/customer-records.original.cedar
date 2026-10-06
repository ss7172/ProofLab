permit(
  principal,
  action == Action::"invoke",
  resource
) unless {
  context has toolName && !["customer-records___customer_lookup"].contains(context.toolName)
} unless {
  resource has dataClassification && resource.dataClassification == "restricted"
};
