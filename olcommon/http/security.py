from pyramid.authorization import ACLHelper


class SecurityPolicy:
    
    def identity(self, request):
        return None

    def permits(self,request, context, permission):
        principals = request.root.principals_for_identity(request.identity)
        return ACLHelper().permits(context, principals, permission)
