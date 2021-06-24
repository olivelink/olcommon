from pyramid.authorization import ACLHelper


class SecurityPolicy:

    def authenticated_userid(self, request):
        identity = request.identity
        if identity:
            return identity.authenticated_userid
        else:
            return None
    
    def identity(self, request):
        claims = request.jwt_claims
        if claims and "access" in claims.get("aud", []):
            return request.root.identity_for_jwt_claims(claims)
        return None

    def permits(self,request, context, permission):
        principals = request.root.principals_for_identity(request.identity)
        return ACLHelper().permits(context, principals, permission)
