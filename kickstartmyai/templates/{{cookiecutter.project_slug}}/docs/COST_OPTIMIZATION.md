# 💰 Cost Optimization Guide

This guide helps you keep AWS costs under **$50-100/month** while maintaining production-ready infrastructure.

## 📊 **Estimated Monthly Costs**

### **Core Infrastructure (Always Running)**
| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| ECS Fargate | 1 task (0.25 vCPU, 0.5GB) 24/7 | ~$9 |
| RDS PostgreSQL | db.t3.micro, 20GB gp3 | ~$15 |
| ElastiCache Redis | cache.t3.micro | ~$12 |
| Application Load Balancer | 1 ALB | ~$18 |
| NAT Gateway | 1 NAT Gateway | ~$32 |
| **Base Infrastructure Total** | | **~$86/month** |

### **Additional Costs (Usage-Based)**
| Service | Cost |
|---------|------|
| CloudWatch Logs (7-day retention) | $1-3/month |
| ACM SSL Certificate | Free |
| Route53 Hosted Zone | $0.50/month |
| Data Transfer | $1-5/month |
| **Total with Basic Usage** | **~$90-95/month** |

### **Cost Optimization Features**
| Feature | Savings |
|---------|---------|
| Single AZ deployment | -$32/month (1 NAT Gateway) |
| gp3 storage vs gp2 | -$1-2/month |
| 7-day log retention vs 30-day | -$5-10/month |
| Scheduled scaling (night/weekend) | -10-20% compute costs |
| Spot instances (optional) | -50-70% compute costs |

## 🎯 **Cost Control Strategies**

### **1. Auto-Scaling Configuration**
```terraform
# Aggressive scaling down during low usage
min_capacity = 1
max_capacity = 3
```

### **2. Scheduled Scaling**
- **Night Hours (2 AM - 8 AM UTC)**: Scale down to 1 instance
- **Business Hours (8 AM - 10 PM UTC)**: Scale up as needed
- **Weekends**: Reduced capacity

### **3. Resource Right-Sizing**
- **ECS Tasks**: 256 CPU, 512 MB memory (smallest Fargate size)
- **RDS**: db.t3.micro with burstable performance
- **Redis**: cache.t3.micro (single node)

### **4. Storage Optimization**
- **RDS**: gp3 storage (more cost-effective than gp2)
- **Storage Auto-scaling**: Prevents over-provisioning
- **Backup Retention**: 7 days (reduced from default 35)

## 📈 **Cost Monitoring & Alerts**

### **Automated Cost Controls**
1. **AWS Budget**: $100/month with 80% alert threshold
2. **Cost Anomaly Detection**: Alerts for unusual spending
3. **CloudWatch Cost Metrics**: Daily cost tracking
4. **GitHub Actions Cost Check**: CI/CD pipeline cost validation

### **Budget Alert Configuration**
```terraform
resource "aws_budgets_budget" "monthly_cost" {
  limit_amount = 100
  limit_unit   = "USD"
  
  notification {
    threshold = 80  # Alert at 80% of budget
    threshold_type = "PERCENTAGE"
    subscriber_email_addresses = ["your-email@example.com"]
  }
}
```

## 🔧 **Implementation Steps**

### **1. Set Up Cost Monitoring**
```bash
# Deploy with cost monitoring enabled
terraform apply -var="enable_cost_monitoring=true"
```

### **2. Configure Budget Alerts**
```bash
# Set your email for budget alerts
terraform apply -var="alert_email_addresses=[\"your-email@example.com\"]"
```

### **3. Enable Auto-Scaling**
```bash
# Enable cost-effective auto-scaling
terraform apply -var="enable_ecs_auto_scaling=true"
terraform apply -var="enable_scheduled_scaling=true"
```

## ⚠️ **Cost Warnings & Limits**

### **Services to Monitor**
1. **Data Transfer**: Can spike with high API usage
2. **CloudWatch Logs**: Verbose logging increases costs
3. **RDS Storage**: Auto-scaling can increase costs
4. **ECS Task Scaling**: Monitor max instances

### **Cost Spike Prevention**
```bash
# Set maximum limits in terraform
max_capacity = 3  # Prevent runaway scaling
log_retention_days = 7  # Minimize log storage
enable_detailed_monitoring = false  # Disable expensive monitoring
```

## 💡 **Additional Cost Savings**

### **1. Use AWS Free Tier**
- **CloudWatch**: 5GB of logs per month free
- **ACM**: SSL certificates are free
- **Route53**: First hosted zone is $0.50/month
- **Data Transfer**: 100GB out per month free

### **2. Optimize for Your Usage Pattern**
```bash
# For development/testing environments
desired_count = 0  # Scale to zero when not in use

# For low-traffic production
desired_count = 1
max_capacity = 2
```

### **3. Consider Reserved Instances**
For stable workloads, RDS Reserved Instances can save 30-60%:
- 1-year term: ~30% savings
- 3-year term: ~60% savings

### **4. Spot Instances (Advanced)**
For fault-tolerant workloads, use Spot instances for additional savings:
```terraform
# ECS Spot capacity providers (advanced configuration)
capacity_providers = ["FARGATE_SPOT"]
```

## 📊 **Cost Optimization Checklist**

### **Before Deployment**
- [ ] Review all resource configurations
- [ ] Set up budget alerts
- [ ] Configure auto-scaling policies
- [ ] Enable cost monitoring

### **Weekly Monitoring**
- [ ] Check AWS Cost Explorer
- [ ] Review budget alerts
- [ ] Monitor resource utilization
- [ ] Adjust scaling policies if needed

### **Monthly Review**
- [ ] Analyze cost trends
- [ ] Right-size resources based on usage
- [ ] Review and optimize log retention
- [ ] Consider Reserved Instances for stable workloads

## 🚨 **Emergency Cost Controls**

If costs exceed budget:

### **Immediate Actions**
1. **Scale down ECS service**: `aws ecs update-service --desired-count 1`
2. **Reduce log retention**: Update CloudWatch log groups to 1-day retention
3. **Disable detailed monitoring**: Turn off enhanced monitoring

### **Terraform Emergency Commands**
```bash
# Quick scale down
terraform apply -var="desired_count=1" -var="max_capacity=1"

# Disable expensive features
terraform apply -var="enable_detailed_monitoring=false"
terraform apply -var="log_retention_days=1"
```

## 📞 **Support & Resources**

- **AWS Cost Calculator**: https://calculator.aws/
- **AWS Cost Explorer**: Monitor actual spending
- **AWS Trusted Advisor**: Cost optimization recommendations
- **This Template's Cost Dashboard**: Included in CloudWatch module

---

**Remember**: This configuration prioritizes cost optimization while maintaining production readiness. Monitor your actual usage and adjust resources accordingly.