effective_principals

if acl and callable(acl):
    acl = acl()

for ace in acl:
    ace_action, ace_principal, ace_permissions = ace
    if ace_principal in principals:
        if not is_nonstr_iter(ace_permissions):
            ace_permissions = [ace_permissions]
        if permission in ace_permissions:
            if ace_action == Allow:
                return ACLAllowed(
                    ace, acl, permission, principals, location
                )
            else:
                return ACLDenied(
                    ace, acl, permission, principals, location
                )

