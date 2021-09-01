from pyramid.authorization import ACLHelper


class SecurityPolicy:

    def authenticated_userid(self, request):
        claims = request.jwt_claims
        if claims:
            return request.site.authenticated_userid_for_jwt_claims(claims)
        return None
        
    def identity(self, request):
        claims = request.jwt_claims
        if claims and "access" in claims.get("aud", []):
            return request.site.identity_for_jwt_claims(claims)
        return None

    def permits(self,request, context, permission):
        claims = request.jwt_claims
        principals = request.site.principals_for_identity(request.identity, claims)
        return ACLHelper().permits(context, principals, permission)
