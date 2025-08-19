# Use the official .NET 8 runtime as base image
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
WORKDIR /app
EXPOSE 80
EXPOSE 443

# Use the .NET 8 SDK for building
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY ["retail-rag-web-app.csproj", "."]
RUN dotnet restore "./retail-rag-web-app.csproj"
COPY . .
WORKDIR "/src/."
RUN dotnet build "retail-rag-web-app.csproj" -c Release -o /app/build

# Publish the app
FROM build AS publish
RUN dotnet publish "retail-rag-web-app.csproj" -c Release -o /app/publish /p:UseAppHost=false

# Final stage/image
FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV ASPNETCORE_ENVIRONMENT=Production
ENV ASPNETCORE_URLS=http://+:80

ENTRYPOINT ["dotnet", "retail-rag-web-app.dll"]
