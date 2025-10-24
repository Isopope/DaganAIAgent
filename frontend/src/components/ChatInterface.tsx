import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, User, Lightbulb } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { SourcesFavicons, Source } from "./SourcesFavicons";
import { CitationsPanel } from "./CitationsPanel";
import { StreamingMessage } from "./StreamingMessage";
import { ToolPipeline } from "./ToolPipeline";
import avatarImage from "@/assets/avatar.svg";
import rienImage from "@/assets/rien.svg";
import reflexionImage from "@/assets/reflexion.svg";
import logoImage from "@/assets/Novatekis.svg";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface ToolStep {
  type: "validate_domain" | "agent_rag" | "vector_search" | "web_search" | "generate";
  status: "pending" | "active" | "completed";
  count?: number;
  details?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  toolSteps?: ToolStep[];
}

const SUGGESTED_QUESTIONS = [
  "Comment renouveler mon passeport ?",
  "Comment obtenir un duplicata d'un certificat de nationalité ?",
  "Demande d'abonnement à la fibre optique  de YAS TOGO",
  "Quelle est la procédure pour étudier en France pour un étudiant Togolais ?"
];

export const ChatInterface = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [selectedSources, setSelectedSources] = useState<Source[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentToolSteps, setCurrentToolSteps] = useState<ToolStep[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // Restore previous conversation from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("chatMessages");
      const storedConvId = localStorage.getItem("conversationId");
      if (stored) {
        const parsed: Message[] = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setMessages(parsed);
        }
      }
      if (storedConvId) {
        setConversationId(storedConvId);
      }
    } catch (e) {
      // ignore
    }
  }, []);

  // Persist conversation locally on changes
  useEffect(() => {
    try {
      localStorage.setItem("chatMessages", JSON.stringify(messages));
      if (conversationId) {
        localStorage.setItem("conversationId", conversationId);
      }
    } catch (e) {
      // ignore
    }
  }, [messages, conversationId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (text?: string) => {
    const payload = (text ?? input).trim();
    if (!payload || isLoading) return;

    const userMessage: Message = { role: "user", content: payload };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    
    // Réinitialiser les étapes du pipeline
    setCurrentToolSteps([]);

    let accumulatedContent = "";
    let collectedSources: Source[] = [];
    let toolStepsMap = new Map<string, ToolStep>();

    try {
      const apiUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      const requestBody: any = { question: payload };
      if (conversationId) {
        requestBody.conversation_id = conversationId;
      }
      
      const response = await fetch(`${apiUrl}/crag/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("No response body");
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.trim()) continue;

          try {
            const event = JSON.parse(line);

            // Gérer les événements de status pour le pipeline
            if (event.type === "status") {
              const stepType = event.step as ToolStep["type"];
              
              // Marquer l'étape précédente comme completed si elle existe
              toolStepsMap.forEach((step) => {
                if (step.status === "active") {
                  step.status = "completed";
                }
              });
              
              // Ajouter ou mettre à jour l'étape actuelle
              if (!toolStepsMap.has(stepType)) {
                toolStepsMap.set(stepType, {
                  type: stepType,
                  status: "active",
                  count: 1,
                  details: event.message
                });
              } else {
                const existingStep = toolStepsMap.get(stepType)!;
                existingStep.status = "active";
                existingStep.count = (existingStep.count || 0) + 1;
              }
              
              // Mettre à jour le state avec les étapes en ordre
              const orderedSteps = Array.from(toolStepsMap.values());
              setCurrentToolSteps([...orderedSteps]);
            }
            
            if (event.type === "message_chunk") {
              accumulatedContent += event.content;
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMsg = newMessages[newMessages.length - 1];
                
                if (lastMsg && lastMsg.role === "assistant") {
                  lastMsg.content = accumulatedContent;
                  lastMsg.toolSteps = Array.from(toolStepsMap.values());
                } else {
                  newMessages.push({
                    role: "assistant",
                    content: accumulatedContent,
                    sources: [],
                    toolSteps: Array.from(toolStepsMap.values())
                  });
                }
                return newMessages;
              });
            } else if (event.type === "complete") {
              collectedSources = event.sources || [];
              
              // Marquer toutes les étapes comme completed
              toolStepsMap.forEach((step) => {
                step.status = "completed";
              });
              
              // Capture and persist conversation_id from backend
              if (event.conversation_id) {
                setConversationId(event.conversation_id);
              }
              
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMsg = newMessages[newMessages.length - 1];
                if (lastMsg && lastMsg.role === "assistant") {
                  lastMsg.content = event.answer;
                  lastMsg.sources = collectedSources;
                  lastMsg.toolSteps = Array.from(toolStepsMap.values());
                }
                return newMessages;
              });
              
              // Nettoyer le pipeline actuel une fois terminé
              setCurrentToolSteps([]);
            } else if (event.type === "error") {
              throw new Error(event.message || "Server error");
            }
          } catch (parseError) {
            console.warn("Failed to parse event:", line);
          }
        }
      }
    } catch (error: any) {
      console.error("Error sending message:", error);
      toast({
        title: "Erreur",
        description: error?.message || "Une erreur est survenue lors de l'envoi du message.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleSuggestionClick = (question: string) => {
    setInput(question);
    
  };

  const handleClearConversation = () => {
    setMessages([]);
    setConversationId(null);
    try {
      localStorage.removeItem("chatMessages");
      localStorage.removeItem("conversationId");
    } catch (e) {

    }
  };

  const handleSourceClick = (sources: Source[]) => {
    setSelectedSources(sources);
    setIsPanelOpen(true);
  };

  // Fonction pour déterminer l'avatar à afficher selon l'état du pipeline
  const getAvatarForSteps = (steps?: ToolStep[]) => {
    if (!steps || steps.length === 0) return rienImage;
    
    // Si on est en train de générer (generate active ou completed), utiliser avatar.svg
    const hasGenerateActive = steps.some(s => s.type === "generate" && (s.status === "active" || s.status === "completed"));
    if (hasGenerateActive) return avatarImage;
    
    // Si on a des étapes de recherche actives, utiliser reflexion.svg
    const hasActiveSearch = steps.some(s => 
      (s.type === "validate_domain" || s.type === "agent_rag" || s.type === "vector_search" || s.type === "web_search") 
      && s.status === "active"
    );
    if (hasActiveSearch) return reflexionImage;
    
    // Par défaut, rien.svg
    return rienImage;
  };

  return (
    <>
    <Card className={`w-full shadow-2xl border-2 my-8 bg-white/95 backdrop-blur-sm transition-all duration-300 ${isPanelOpen ? 'max-w-[calc(100%-410px)] mr-[390px]' : 'max-w-[calc(100%-20px)]'}`}>
      <CardHeader className="flex flex-row items-center justify-between px-4 py-2 border-b bg-white">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Développé par</span>
          <img src={logoImage} alt="Novatekis" className="h-10 w-auto" />
        </div>
        <div className="flex items-center gap-2">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="sm" disabled={isLoading}>
                Nouvelle conversation
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Nouvelle conversation</AlertDialogTitle>
                <AlertDialogDescription>
                  Êtes-vous sûr de vouloir commencer une nouvelle conversation ? 
                  L'historique actuel sera supprimé et vous n'aurez plus accès à cette conversation.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Annuler</AlertDialogCancel>
                <AlertDialogAction onClick={handleClearConversation}>
                  Continuer
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[60vh] p-4" ref={scrollRef}>
          <div className="space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-4 space-y-3">
                <div className="text-center space-y-2">
                  <div className="inline-flex items-center justify-center w-56 h-56 mb-0.5">
                    <img src={avatarImage} alt="Dagan Avatar" className="h-48 w-48" />
                  </div>
                  <h2 className="text-lg font-bold text-foreground">Woezon, Bonjour je suis Dagan votre assistant IA</h2>
                  <p className="text-xs text-muted-foreground max-w-md mx-auto">
                    Assistant intelligent pour vos démarches administratives au Togo.
                  </p>
                </div>
                
                <div className="w-full max-w-2xl space-y-2">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground justify-center">
                    <Lightbulb className="h-3 w-3 text-warning" />
                    <span>Questions suggérées :</span>
                  </div>
                  <div className="grid gap-2">
                    {SUGGESTED_QUESTIONS.map((question, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSuggestionClick(question)}
                        className="text-left px-3 py-2 rounded-lg border-2 border-primary/20 bg-white hover:bg-highlight hover:border-accent hover:shadow-2xl hover:shadow-accent/50 hover:scale-[1.05] transition-all duration-300 text-xs text-foreground font-medium group relative overflow-hidden"
                      >
                        <span className="relative z-10">{question}</span>
                        <div className="absolute inset-0 bg-gradient-to-r from-accent/0 via-accent/30 to-accent/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out"></div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <>
                {messages.map((message, index) => (
              <div
                key={index}
                className={`flex gap-3 ${
                  message.role === "user" ? "justify-end" : "justify-start"
                } animate-fade-in`}
              >
                {message.role === "assistant" && (
                  <div className="h-10 w-10 flex items-center justify-center flex-shrink-0">
                    <img src={getAvatarForSteps(message.toolSteps)} alt="Dagan" className="h-9 w-9" />
                  </div>
                )}
                
                <div
                  className={`rounded-xl px-3 py-2 max-w-[80%] ${
                    message.role === "user"
                      ? "bg-[#86b7b2] text-white"
                      : "bg-white border shadow-sm"
                  }`}
                >
                  <div className="flex flex-col">
                    {/* Afficher le pipeline d'outils si disponible */}
                    {message.role === "assistant" && message.toolSteps && message.toolSteps.length > 0 && (
                      <ToolPipeline steps={message.toolSteps} />
                    )}
                    
                    {message.role === "assistant" ? (
                      <StreamingMessage content={message.content} />
                    ) : (
                      <p className="text-xs leading-relaxed whitespace-pre-wrap">
                        {message.content}
                      </p>
                    )}
                    {message.role === "assistant" && message.sources && message.sources.length > 0 && (
                      <SourcesFavicons sources={message.sources} onSourceClick={handleSourceClick} />
                    )}
                  </div>
                </div>
                
                {message.role === "user" && (
                  <div className="h-8 w-8 rounded-full bg-primary/15 flex items-center justify-center flex-shrink-0">
                    <User className="h-5 w-5 text-primary" />
                  </div>
                )}
              </div>
            ))}
            
                {/* Afficher le pipeline en temps réel pendant le streaming */}
                {isLoading && currentToolSteps.length > 0 && (
                  <div className="flex gap-3 justify-start animate-fade-in">
                    <div className="h-10 w-10 flex items-center justify-center flex-shrink-0">
                      <img src={getAvatarForSteps(currentToolSteps)} alt="Dagan" className="h-9 w-9" />
                    </div>
                    <div className="rounded-xl px-3 py-2 max-w-[80%] bg-white border shadow-sm">
                      <ToolPipeline steps={currentToolSteps} />
                    </div>
                  </div>
                )}
            
                {isLoading && currentToolSteps.length === 0 && (
                  <div className="flex gap-3 justify-start animate-fade-in">
                    <div className="h-10 w-10 flex items-center justify-center">
                      <img src={rienImage} alt="Dagan" className="h-9 w-9" />
                    </div>
                    <div className="rounded-xl px-4 py-3 bg-white border shadow-sm">
                      <div className="flex gap-1">
                        <div className="h-2 w-2 rounded-full bg-accent/60 animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="h-2 w-2 rounded-full bg-accent/60 animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="h-2 w-2 rounded-full bg-accent/60 animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </ScrollArea>
        
        <div className="p-3 border-t">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Posez votre question..."
              disabled={isLoading}
              className="flex-1 text-xs"
            />
            <Button 
              onClick={() => sendMessage()} 
              disabled={isLoading || !input.trim()}
              size="icon"
              className="flex-shrink-0 bg-[#025253] hover:bg-[#025253]/90"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
    
    <CitationsPanel
      sources={selectedSources}
      isOpen={isPanelOpen}
      onClose={() => setIsPanelOpen(false)}
    />
    </>
  );
};
