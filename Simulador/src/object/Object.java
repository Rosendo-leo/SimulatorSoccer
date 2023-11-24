package object;

import java.awt.Graphics;
import java.awt.Rectangle;
import java.awt.image.BufferedImage;

import javafx.scene.shape.Circle;


public class Object {
	
public static int maskx,masky,mwidth,mheight;
	
	protected double x;
	protected double y;
	protected int width;
	protected int height;
	
	private BufferedImage sprite;
	
	public Object(int x, int y, int width, int height, BufferedImage sprite) {
		this.x = x;
		this.y = y;
		this.width = width;
		this.height = height;
		this.sprite = sprite;
		
		Object.maskx = 8;
		Object.masky = 8;
		Object.mwidth = 10;
		Object.mheight = 10;
	}
	
	public int getX() {
		return (int)this.x;
	}
	
	public int getY() {
		return (int)this.y;
	}
	
	public int getWidth() {
		return this.width;
	}
	
	public int getHeght() {
		return this.height;
	}

	public void tick() {
		
	}
	
	public double calculateDistance(int x1, int y1, int x2, int y2) {
		return Math.sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
	}
	
	public static boolean isColliding(Object e1, Object e2) {
		Circle e1Mask = new Circle(e1.getX() + Object.maskx, e1.getY() + Object.masky, mwidth);
		Circle e2Mask = new Circle(e2.getX() + Object.maskx, e2.getY() + Object.masky, mwidth);
		
		return e1Mask.intersects(e2Mask);
	}
	
	public void render(Graphics g) {
		g.drawImage(sprite, this.getX(), this.getY(), null);
	}
	
	public void setX(int newX) {
		this.x = newX;
	}
	
	public void setY(int newY) {
		this.y = newY;
	}

}
