from flask import jsonify


def register_jwt_handlers(jwt):
    """Register JWT error handlers"""
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """Handler for expired tokens"""
        token_type = jwt_payload.get('type', 'access')
        return jsonify({
            'error': 'Token expired',
            'message': f'The {token_type} token has expired. Please {"login again" if token_type == "refresh" else "refresh your token"}.'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """Handler for invalid tokens"""
        return jsonify({
            'error': 'Invalid token',
            'message': 'The token signature is invalid or the token is malformed. Please login again.'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        """Handler for missing tokens"""
        return jsonify({
            'error': 'Authorization required',
            'message': 'Access token is missing. Please provide a valid Bearer token in the Authorization header.'
        }), 401
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        """Handler for revoked tokens"""
        return jsonify({
            'error': 'Token revoked',
            'message': 'This token has been revoked. Please login again.'
        }), 401
    
    @jwt.token_verification_failed_loader
    def token_verification_failed_callback(jwt_header, jwt_payload):
        """Handler for token verification failures"""
        return jsonify({
            'error': 'Token verification failed',
            'message': 'Token verification failed. The token may be corrupted or tampered with.'
        }), 401
    
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        """Handler for non-fresh tokens"""
        return jsonify({
            'error': 'Fresh token required',
            'message': 'This action requires a fresh token. Please login again.'
        }), 401

