import { Button } from "@/components/ui/button";
import { MessageSquare, ArrowRight } from "lucide-react";

interface HeroProps {
  onStartChat: () => void;
}

export const Hero = ({ onStartChat }: HeroProps) => {
  return (
    <section className="relative min-h-[80vh] flex items-center justify-center px-4 sm:px-6 lg:px-8 bg-primary bg-leaf-pattern">
      <div className="absolute inset-0 bg-gradient-to-b from-primary/95 to-primary/98" />
      
      <div className="relative max-w-5xl mx-auto text-center space-y-8 animate-fade-in">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 text-white text-sm font-medium mb-4 backdrop-blur-sm border border-white/20">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-secondary"></span>
          </span>
          Intelligence artificielle au service des citoyens
        </div>
        
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-white">
          Votre plateforme de services
          <span className="block mt-2 text-secondary">
            gouvernementaux
          </span>
        </h1>
        
        <p className="text-lg sm:text-xl text-white/90 max-w-2xl mx-auto leading-relaxed">
          Simplifiez vos démarches administratives avec CivIA, votre assistant IA conversationnel.
          Informations actualisées, langage simplifié, disponible 24/7.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-4">
          <Button 
            size="lg" 
            onClick={onStartChat}
            className="group px-8 py-6 text-lg bg-secondary hover:bg-secondary/90 text-white shadow-lg hover:shadow-xl transition-all duration-300 border-0"
          >
            <MessageSquare className="mr-2 h-5 w-5" />
            Commencer une discussion
            <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
          </Button>
          
          <Button 
            size="lg" 
            variant="outline"
            className="px-8 py-6 text-lg border-2 border-white/30 text-white hover:bg-white/10 backdrop-blur-sm"
          >
            En savoir plus
          </Button>
        </div>
        
        <div className="pt-8 flex flex-wrap items-center justify-center gap-6 text-sm text-white/80">
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-secondary" />
            <span>100% gratuit</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-secondary" />
            <span>Disponible 24/7</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-secondary" />
            <span>Données sécurisées</span>
          </div>
        </div>
      </div>
    </section>
  );
};
