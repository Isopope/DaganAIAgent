import { MessageSquare, Globe, RefreshCw, FileText, Shield } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const features = [
  {
    icon: MessageSquare,
    title: "Chatbot IA conversationnel",
    description: "Posez vos questions en langage naturel et obtenez des réponses claires et précises adaptées à votre situation."
  },
  {
    icon: RefreshCw,
    title: "Scraping régulier",
    description: "Extraction automatique et mise à jour continue des informations depuis les sites publics officiels."
  },
  {
    icon: Globe,
    title: "Intégration directe",
    description: "Les changements détectés sont immédiatement intégrés dans les réponses pour une information toujours à jour."
  },
  {
    icon: FileText,
    title: "Simplification du langage",
    description: "Reformulation automatique des textes administratifs complexes en langage clair et compréhensible."
  },
  {
    icon: Shield,
    title: "Fiable et sécurisé",
    description: "Basé uniquement sur des sources officielles vérifiées. Vos données restent privées et sécurisées."
  }
];

export const Features = () => {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-muted/30">
      <div className="max-w-7xl mx-auto">
        <div className="text-center space-y-4 mb-16 animate-fade-in">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground">
            Comment fonctionne CivIA ?
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Une solution complète pour simplifier toutes vos démarches administratives
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <Card 
                key={index}
                className="group hover:shadow-lg transition-all duration-300 hover:-translate-y-1 border animate-fade-in bg-white"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <CardContent className="p-6 space-y-4">
                  <div className="h-14 w-14 rounded-lg bg-accent/10 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                    <Icon className="h-7 w-7 text-accent stroke-[2]" />
                  </div>
                  
                  <h3 className="text-xl font-semibold text-foreground">
                    {feature.title}
                  </h3>
                  
                  <p className="text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
};
