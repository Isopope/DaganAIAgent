import React from "react";
import { CheckCircle2, LoaderCircle, ArrowRight, Search, Database, Sparkles } from "lucide-react";

interface ToolStep {
  type: "validate_domain" | "agent_rag" | "vector_search" | "web_search" | "generate" | "route_question" | "casual_convo";
  status: "pending" | "active" | "completed";
  count?: number;
  details?: string;
}

interface ToolPipelineProps {
  steps: ToolStep[];
}

// Définition des catégories regroupées
const STEP_CATEGORIES = {
  analyse: {
    label: "Analyse",
    icon: Search,
    steps: ["route_question", "validate_domain"]
  },
  recherche: {
    label: "Recherche", 
    icon: Database,
    steps: ["agent_rag", "vector_search", "web_search"]
  },
  generation: {
    label: "Génération",
    icon: Sparkles,
    steps: ["casual_convo", "generate"]
  }
} as const;

type CategoryKey = keyof typeof STEP_CATEGORIES;

export const ToolPipeline: React.FC<ToolPipelineProps> = ({ steps }) => {
  // Fonction pour regrouper les étapes par catégories
  const getGroupedSteps = () => {
    const grouped: Record<CategoryKey, { status: "pending" | "active" | "completed"; count: number }> = {
      analyse: { status: "pending", count: 0 },
      recherche: { status: "pending", count: 0 },
      generation: { status: "pending", count: 0 }
    };

    // Pour chaque étape reçue, l'ajouter à sa catégorie
    steps.forEach(step => {
      let category: CategoryKey | null = null;
      
      if (STEP_CATEGORIES.analyse.steps.includes(step.type as any)) {
        category = "analyse";
      } else if (STEP_CATEGORIES.recherche.steps.includes(step.type as any)) {
        category = "recherche";
      } else if (STEP_CATEGORIES.generation.steps.includes(step.type as any)) {
        category = "generation";
      }

      if (category) {
        const cat = grouped[category];
        cat.count += step.count || 1;
        
        // Logique de priorité de statut : completed > active > pending
        if (step.status === "completed" || (step.status === "active" && cat.status === "pending")) {
          cat.status = step.status;
        }
      }
    });

    // Convertir en tableau et filtrer les catégories vides
    return Object.entries(grouped)
      .filter(([_, data]) => data.count > 0)
      .map(([key, data]) => ({
        key: key as CategoryKey,
        ...data
      }));
  };

  const getStepIcon = (categoryKey: CategoryKey, status: string) => {
    const IconComponent = STEP_CATEGORIES[categoryKey].icon;
    const iconClass = "h-4 w-4";
    
    if (status === "completed") {
      return <CheckCircle2 className={`${iconClass} text-green-500`} />;
    }
    
    if (status === "active") {
      return <LoaderCircle className={`${iconClass} animate-spin text-blue-500`} />;
    }

    return <IconComponent className={`${iconClass} text-gray-300`} />;
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

  const groupedSteps = getGroupedSteps();

  if (groupedSteps.length === 0) return null;

  return (
    <div className="flex items-center space-x-2 py-2 px-3 bg-gradient-to-r from-blue-50/50 to-indigo-50/50 rounded-lg mb-3 border border-blue-100/50">
      <div className="flex items-center space-x-2 flex-wrap">
        {groupedSteps.map((groupedStep, index) => (
          <React.Fragment key={groupedStep.key}>
            <div className="flex items-center space-x-1.5">
              {getStepIcon(groupedStep.key, groupedStep.status)}
              <span className={`text-xs font-medium ${getStepColor(groupedStep.status)}`}>
                {STEP_CATEGORIES[groupedStep.key].label}
                {groupedStep.count > 1 && (
                  <span className="ml-1 text-gray-500">({groupedStep.count})</span>
                )}
              </span>
            </div>
            {index < groupedSteps.length - 1 && (
              <ArrowRight className="h-3 w-3 text-gray-400" />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};
