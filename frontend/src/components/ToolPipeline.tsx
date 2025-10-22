import React from "react";
import { CheckCircle2, LoaderCircle, ArrowRight, Search, Database, Globe, Sparkles, ShieldCheck } from "lucide-react";

interface ToolStep {
  type: "validate_domain" | "agent_rag" | "vector_search" | "web_search" | "generate";
  status: "pending" | "active" | "completed";
  count?: number;
  details?: string;
}

interface ToolPipelineProps {
  steps: ToolStep[];
}

export const ToolPipeline: React.FC<ToolPipelineProps> = ({ steps }) => {
  const getStepIcon = (type: string, status: string) => {
    const iconClass = "h-4 w-4";
    
    if (status === "completed") {
      return <CheckCircle2 className={`${iconClass} text-green-500`} />;
    }
    
    if (status === "active") {
      return <LoaderCircle className={`${iconClass} animate-spin text-blue-500`} />;
    }

    // Icons par type d'étape (pending)
    switch (type) {
      case "validate_domain":
        return <ShieldCheck className={`${iconClass} text-gray-300`} />;
      case "agent_rag":
        return <Sparkles className={`${iconClass} text-gray-300`} />;
      case "vector_search":
        return <Database className={`${iconClass} text-gray-300`} />;
      case "web_search":
        return <Globe className={`${iconClass} text-gray-300`} />;
      case "generate":
        return <Search className={`${iconClass} text-gray-300`} />;
      default:
        return <div className="h-4 w-4 rounded-full border-2 border-gray-300" />;
    }
  };

  const getStepLabel = (type: string) => {
    switch (type) {
      case "validate_domain":
        return "Validation";
      case "agent_rag":
        return "Agent CRAG";
      case "vector_search":
        return "Recherche vectorielle";
      case "web_search":
        return "Recherche web";
      case "generate":
        return "Génération";
      default:
        return type;
    }
  };

  const getStepColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-green-600";
      case "active":
        return "text-blue-600";
      default:
        return "text-gray-400";
    }
  };

  if (steps.length === 0) return null;

  return (
    <div className="flex items-center space-x-2 py-2 px-3 bg-gradient-to-r from-blue-50/50 to-indigo-50/50 rounded-lg mb-3 border border-blue-100/50">
      <div className="flex items-center space-x-2 flex-wrap">
        {steps.map((step, index) => (
          <React.Fragment key={index}>
            <div className="flex items-center space-x-1.5">
              {getStepIcon(step.type, step.status)}
              <span className={`text-xs font-medium ${getStepColor(step.status)}`}>
                {getStepLabel(step.type)}
                {step.count !== undefined && step.count > 0 && (
                  <span className="ml-1 text-gray-500">({step.count})</span>
                )}
              </span>
            </div>
            {index < steps.length - 1 && (
              <ArrowRight className="h-3 w-3 text-gray-400" />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};
