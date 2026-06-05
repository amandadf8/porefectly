# image Nginx sebagai base 
FROM nginx:alpine

# Copy semua file frontend ke folder default Nginx
COPY . /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Jalankan Nginx
CMD ["nginx", "-g", "daemon off;"]