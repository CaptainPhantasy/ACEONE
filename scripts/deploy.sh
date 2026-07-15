#!/bin/bash

# ClaudeVoice Deployment Script
# Deploys the agent and webhook to production

set -e

echo "=================================="
echo "ClaudeVoice Production Deployment"
echo "=================================="

# Configuration
DEPLOY_ENV=${1:-production}
AGENT_IMAGE="gcr.io/claudevoice/agent"
WEBHOOK_URL="https://claudevoice-webhook.vercel.app"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check environment file
    if [ ! -f ".env.$DEPLOY_ENV" ]; then
        log_error ".env.$DEPLOY_ENV file not found"
        exit 1
    fi

    # Check LiveKit CLI
    if ! command -v lk &> /dev/null; then
        log_warn "LiveKit CLI not installed. Install with: brew install livekit-cli"
    fi

    log_info "Prerequisites check passed"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."

    # Build agent image
    docker build -f docker/Dockerfile.agent -t "${AGENT_IMAGE}:latest" .
    docker tag "${AGENT_IMAGE}:latest" "${AGENT_IMAGE}:$(git rev-parse --short HEAD)"

    log_info "Docker images built successfully"
}

# Run tests
run_tests() {
    log_info "Running tests..."

    # Run Python tests
    docker run --rm \
        --env-file .env.$DEPLOY_ENV \
        "${AGENT_IMAGE}:latest" \
        python -m pytest tests/ -v

    # Run E2E tests
    chmod +x tests/e2e/test_call_flow.sh
    ./tests/e2e/test_call_flow.sh

    log_info "All tests passed"
}

# Deploy agent to Cloud Run
deploy_agent() {
    log_info "Deploying agent to Cloud Run..."

    # Push to GCR
    docker push "${AGENT_IMAGE}:latest"
    docker push "${AGENT_IMAGE}:$(git rev-parse --short HEAD)"

    # Deploy to Cloud Run
    gcloud run deploy claudevoice-agent \
        --image "${AGENT_IMAGE}:latest" \
        --platform managed \
        --region us-central1 \
        --allow-unauthenticated \
        --set-env-vars-from-file .env.$DEPLOY_ENV \
        --memory 2Gi \
        --cpu 2 \
        --min-instances 1 \
        --max-instances 10 \
        --concurrency 10

    # Get service URL
    AGENT_URL=$(gcloud run services describe claudevoice-agent \
        --platform managed \
        --region us-central1 \
        --format 'value(status.url)')

    log_info "Agent deployed to: $AGENT_URL"
}

# Deploy webhook to Vercel
deploy_webhook() {
    log_info "Deploying webhook to Vercel..."

    cd webhook
    npm install
    vercel --prod

    cd ..

    log_info "Webhook deployed to: $WEBHOOK_URL"
}

# Register agent with LiveKit
register_agent() {
    log_info "Registering agent with LiveKit..."

    if command -v lk &> /dev/null; then
        lk agent create \
            --name "claudevoice-agent" \
            --url "$AGENT_URL" \
            --api-key "$LIVEKIT_API_KEY" \
            --api-secret "$LIVEKIT_API_SECRET"

        log_info "Agent registered with LiveKit"
    else
        log_warn "Please register agent manually in LiveKit Cloud dashboard"
        log_warn "Agent URL: $AGENT_URL"
    fi
}

# Configure SIP trunk
configure_sip() {
    log_info "Configuring SIP trunk..."

    cat << EOF
Please configure the following in LiveKit Cloud dashboard:

1. Navigate to SIP section
2. Create/Update SIP Trunk
3. Set Inbound Webhook URL: $WEBHOOK_URL/api/sip/inbound
4. Configure dispatch rule:

{
  "dispatch_rule": {
    "rule": {
      "dispatchRuleIndividual": {
        "roomPrefix": "call-"
      }
    },
    "roomConfig": {
      "agents": [
        {
          "agentName": "claudevoice-agent"
        }
      ]
    }
  }
}

5. Purchase/Configure phone number
EOF
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Test agent health
    if curl -f "$AGENT_URL/health" > /dev/null 2>&1; then
        log_info "Agent health check passed"
    else
        log_error "Agent health check failed"
        exit 1
    fi

    # Test webhook health
    if curl -f "$WEBHOOK_URL/api/sip/inbound" > /dev/null 2>&1; then
        log_info "Webhook health check passed"
    else
        log_error "Webhook health check failed"
        exit 1
    fi

    log_info "Deployment verification completed"
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up monitoring..."

    # Deploy Prometheus and Grafana
    docker-compose -f docker/docker-compose.yml up -d prometheus grafana

    log_info "Monitoring setup complete"
    log_info "Grafana: http://localhost:3001 (admin/admin)"
    log_info "Prometheus: http://localhost:9090"
}

# Main deployment flow
main() {
    log_info "Starting deployment for environment: $DEPLOY_ENV"

    check_prerequisites
    build_images
    run_tests
    deploy_agent
    deploy_webhook
    register_agent
    configure_sip
    verify_deployment
    setup_monitoring

    echo ""
    echo "=================================="
    echo -e "${GREEN}Deployment Successful!${NC}"
    echo "=================================="
    echo "Agent URL: $AGENT_URL"
    echo "Webhook URL: $WEBHOOK_URL"
    echo "Environment: $DEPLOY_ENV"
    echo ""
    echo "Next steps:"
    echo "1. Configure SIP trunk in LiveKit dashboard"
    echo "2. Test with a phone call to your configured number"
    echo "3. Monitor logs and metrics"
    echo ""
}

# Handle errors
trap 'log_error "Deployment failed"; exit 1' ERR

# Run main function
main
