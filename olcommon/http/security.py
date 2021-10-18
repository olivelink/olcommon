from pyramid.authorization import ACLHelper


class SecurityPolicy:

    def identity(self, request):
        claims = request.jwt_claims
        if claims and ("access" in (claims.get("aud") or [])):
            return claims
        return None

    def authenticated_userid(self, request):
        if identity := request.identity:
            return identity["sub"]
        return None

    def permits(self,request, context, permission):
        return ACLHelper().permits(context, request.principals, permission)
